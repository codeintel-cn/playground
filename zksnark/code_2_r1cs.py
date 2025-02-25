import ast

def parse(code):
    return ast.parse(code).body

def extract_inputs_and_body(code):
    if len(code) != 1 or not isinstance(code[0], ast.FunctionDef):
        raise Exception("Expection ast body, please check the code")
    
    inputs = []
    for arg in code[0].args.args:
        if isinstance(arg, ast.arg):
            assert isinstance(arg.arg, str)
            inputs.append(arg.arg)
        elif isinstance(arg, ast.Name):
            inputs.append(arg.id)
        else:
            raise Exception("Invalid arg: %r" % ast.dump(arg))
    
    body = []
    returned = False
    for c in code[0].body:
        if not isinstance(c, (ast.Assign, ast.Return)):
            raise Exception("only variable assignment and return are supported")
        if returned:
            raise Exception("Cannot do stuff after a return statement")
        if isinstance(c, ast.Return):
            returned = True
        body.append(c)
    return inputs, body

def flatten_body(body):
    output = []
    for c in body:
        output.extend(flatten_stmt(c))
    return output

next_symbol = [0]
def mksymbol():
    next_symbol[0] += 1
    return 'sym_' + str(next_symbol[0])

def flatten_stmt(stmt):
    target = ''
    if isinstance(stmt, ast.Assign):
        assert len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name)
        target = stmt.targets[0].id
    elif isinstance(stmt, ast.Return):
        target = "~out"
    
    print("------------- stmt", ast.dump(stmt))
    return flatten_expr(target, stmt.value)


def flatten_expr(target, expr):
    # x = y
    if isinstance(expr, ast.Name):
        return [['set', target, expr.id]]
    
    # x = 5
    elif isinstance(expr, ast.Num):
        return [['set', target, expr.n]]
    
    # x = y (op) z
    elif isinstance(expr, ast.BinOp):
        if isinstance(expr.op, ast.Add):
            op = '+'
        elif isinstance(expr.op, ast.Mult):
            op = '*'
        elif isinstance(expr.op, ast.Sub):
            op = '-'
        elif isinstance(expr.op, ast.Div):
            op = '/'
        elif isinstance(expr.op, ast.Pow):
            assert isinstance(expr.right, ast.Num)
            if expr.right.n == 0:
                return [['set', target, 1]]
            elif expr.right.n == 1:
                return flatten_expr(target, expr.left)
            else:
                if isinstance(expr.left, (ast.Name, ast.Num)):
                    nxt = base = expr.left.id if isinstance(expr.left, ast.Name) else expr.left.n
                    o = []
                else:
                    nxt = base = mksymbol()
                    o = flatten_expr(base, expr.left)
                for i in range(1, expr.right.n):
                    latest = nxt
                    nxt = target if i == expr.right.n - 1 else mksymbol()
                    o.append(['*', nxt, latest, base])
                return o
        else:
            raise Exception("bad operation: %s" % ast.dump(expr))
        
        if isinstance(expr.left, (ast.Name, ast.Num)):
            var1 = expr.left.id if isinstance(expr.left, ast.Name) else expr.left.n
            sub1 = []
        else:
            var1 = mksymbol()
            sub1 = flatten_expr(var1, expr.left)
        
        if isinstance(expr.right, (ast.Name, ast.Num)):
            var2 = expr.right.id if isinstance(expr.right, ast.Name) else expr.right.n
            sub2 = []
        return sub1 + sub2 + [[op, target, var1, var2]]
    else:
        raise Exception("unexpected expr : %r" % ast.dump(expr))

def insert_var(arr, varz, var, used, reverse=False):
    if isinstance(var, str):
        if var not in used:
            raise Exception("using a variable before it it set")
        arr[varz.index(var)] += (-1 if reverse else 1)
    elif isinstance(var, int):
        arr[0] += var * (-1 if reverse else 1)

def get_var_replacement(inputs, flatcode):
    return ['~one'] + [x for x in inputs] + ['~out'] + [c[1] for c in flatcode if c[1] not in inputs and c[1] != '~out']

def flatcode_to_r1cs(inputs, flatcode):
    varz = get_var_replacement(inputs, flatcode)
    A, B, C = [], [], []
    used = {i: True for i in inputs}
    for x in flatcode:
        a, b, c = [0] * len(varz), [0] * len(varz), [0] * len(varz)
        if x[1] in used:
            raise Exception("variable already used: %r" % x[1])
        used[x[1]] = True
        if x[0] == 'set':
            a[varz.index(x[1])] += 1
            insert_var(a, varz, x[2], used, reverse=True)
            b[0] = 1
        elif x[0] == '+' or x[0] == '-':
            c[varz.index(x[1])] = 1
            insert_var(a, varz, x[2], used)
            insert_var(a, varz, x[3], used, reverse=(x[0] == '-'))
            b[0] = 1
        elif x[0] == '*':
            c[varz.index(x[1])] = 1
            insert_var(a, varz, x[2], used)
            insert_var(b, varz, x[3], used)
        elif x[0] == '/':
            insert_var(c, varz, x[2], used)
            a[varz.index(x[1])] = 1
            insert_var(b, varz, x[3], used)
        
        A.append(a)
        B.append(b)
        C.append(c)
    return A, B, C


def grab_var(varz, assignment, var):
    if isinstance(var, str):
        return assignment[varz.index(var)]
    elif isinstance(var, int):
        return var
    else:
        raise Exception("What kind of expression is this? %r" % var)

def assign_variables(inputs, input_vars, flatcode):
    varz =get_var_replacement(inputs, flatcode=flatcode)
    assignment = [0] * len(varz)
    assignment[0] = 1
    for i, inp in enumerate(input_vars):
        assignment[i+1] = inp
    
    for x in flatcode:
        if x[0] == 'set':
            assignment[varz.index(x[1])] = grab_var(varz, assignment, x[2])
        elif x[0] == '+':
            assignment[varz.index(x[1])] = grab_var(varz, assignment, x[2]) + grab_var(varz, assignment, x[3])
        elif x[0] == '-':
            assignment[varz.index(x[1])] = grab_var(varz, assignment, x[2]) - grab_var(varz, assignment, x[3])
        elif x[0] == '*':
            assignment[varz.index(x[1])] = grab_var(varz, assignment, x[2]) * grab_var(varz, assignment, x[3])
        elif x[0] == '/':
            assignment[varz.index(x[1])] = grab_var(varz, assignment, x[2]) / grab_var(varz, assignment, x[3])
    
    return assignment

def code_to_r1cs_with_inputs(code, input_vars):
    inputs, body = extract_inputs_and_body(parse(code))
    print("Inputs", inputs)
    print("body", body)
    flatcode = flatten_body(body)
    print("flatcode", flatcode)
    print("input var assignment", get_var_replacement(inputs, flatcode))
    A, B, C = flatcode_to_r1cs(inputs, flatcode)
    r = assign_variables(inputs, input_vars, flatcode)
    return r, A, B, C

code = """
def qeval(x):
    y = x**3
    return y + x + 5
"""
r, A, B, C = code_to_r1cs_with_inputs(code, [3])

print("r", r)
print("A")
for x in A: print(x)
print("B")
for x in B: print(x)
print("C")
for x in C: print(x)

