import sys
import traceback

def atom(x):
    return not isinstance(x, list)

def while_loop(cond, body):
    while eval(cond, env):
        eval(body, env)

def create_global_env():
    return {
        '+': lambda *args: sum(args),
        '-': lambda x, *args: x - sum(args),
        '*': lambda x, y: x * y,
        '/': lambda x, y: x / y,
        '%': lambda x, y: x % y,
        '<': lambda x, y: x < y,
        '>': lambda x, y: x > y,
        'eq': lambda x, y: x == y,
        'append': lambda x, y: x + y,
        'car': lambda lst: lst[0] if isinstance(lst, list) and lst else None,
        'cdr': lambda lst: lst[1:] if isinstance(lst, list) and lst else [],
        'cons': lambda x, y: [x] + (y if isinstance(y, list) else [y]),
        'list': lambda *args: list(args),
        'map': lambda func, lst: [func(x) for x in lst],
        'filter': lambda func, lst: [x for x in lst if func(x)],
        'print': lambda *args: print(*args),
        'while': lambda cond, body: while_loop(cond, body),
    }

def eval(x, env):
    try:
        if atom(x):
            if x == 'nil':
                return False
            if isinstance(x, str):  # Ensure x is a string when looking up symbols
                return env.get(x, x)
            return x  # Return as-is for non-symbol values
        op, *args = x
        #print(f"DEBUG: Evaluating op: {op}, args: {args}")
        if op in env:  # Function call
            proc = eval(op, env)
            #print(f"DEBUG: Found proc: {proc}")
            values = [eval(arg, env) for arg in args]
            #print(f"DEBUG: Values: {values}")
            if callable(proc):
                return proc(*values)
            raise TypeError(f"Attempted to call a non-callable object '{proc}'")
        elif op == 'define':
            if isinstance(args[0], list):  # Check if it's a function definition
                name = args[0][0]  # Function name
                params = args[0][1:]  # Function parameters
                body = args[1:]  # Function body
                env[name] = lambda *vals: eval(['begin'] + body, dict(zip(params, vals), **env))
            else:  # Variable definition
                symbol, exp = args
                env[symbol] = eval(exp, env)
            return None
        elif op == 'lambda':
            params, *body = args
            return lambda *args: eval(['begin'] + body, dict(zip(params, args), **env))
        elif op == 'begin':
            for exp in args[:-1]:
                eval(exp, env)
            return eval(args[-1], env)
        elif op == 'if':
            if len(args) == 2:
                condition, true_branch = args
                false_branch = 'nil'
            elif len(args) == 3:
                condition, true_branch, false_branch = args
            else:
                raise ValueError(f"'if' requires 2 or 3 arguments, got {len(args)}")
            if eval(condition, env):
                return eval(true_branch, env)
            else:
                return eval(false_branch, env)
        elif op == 'cond':
            for clause in args:
                if clause[0] == 't' or eval(clause[0], env):
                    return eval(['begin'] + clause[1:], env)
            return None
        elif op == 'let':
            bindings, *body = args
            local_env = env.copy()
            for symbol, value in bindings:
                local_env[symbol] = eval(value, env)
            return eval(['begin'] + body, local_env)
        elif op == 'set!':
            symbol, value = args
            if symbol in env:
                env[symbol] = eval(value, env)
            else:
                raise NameError(f"Attempting to set an undefined variable '{symbol}'")
            return env[symbol]
        else:
            proc = eval(op, env)
            values = [eval(arg, env) for arg in args]
            print(f"DEBUG: Proc: {proc}, Values: {values}")
            try:
                return proc(*values)
            except TypeError as e:
                raise TypeError(f"Attempted to call a non-callable object '{proc}'. Did you forget to define it or provide a lambda?")
    except Exception as e:
        print(f"Error: {str(e)}")
        print("Traceback:")
        traceback.print_exc()
        return None

def parse(tokens):
    if len(tokens) == 0:
        raise SyntaxError('unexpected EOF')
    token = tokens.pop(0)
    if token == '(':
        L = []
        while tokens[0] != ')':
            L.append(parse(tokens))
        tokens.pop(0)  # pop off ')'
        return L
    elif token == ')':
        raise SyntaxError('unexpected )')
    else:
        return atom_val(token)

def tokenize(s):
    return s.replace('(', ' ( ').replace(')', ' ) ').split()

def read(s):
    return parse(tokenize(s))

def atom_val(token):
    if token == 'nil': return False
    if token == 't': return True
    try:
        return int(token)
    except ValueError:
        try:
            return float(token)
        except ValueError:
            return str(token)

def run_program(program, env=None):
    if env is None:
        env = create_global_env()
    current_expr = ""
    paren_count = 0
    for line in program.split('\n'):
        line = line.strip()
        if not line or line.startswith(';'):
            continue
        current_expr += " " + line
        paren_count += line.count('(') - line.count(')')
        if paren_count == 0:
            try:
                result = eval(read(current_expr), env)
                if result is not None:
                    print(f"Result: {result}")
            except Exception as e:
                print(f"Error in expression '{current_expr}': {str(e)}")
            current_expr = ""
    return env

def repl():
    env = create_global_env()
    while True:
        try:
            user_input = input("lisp> ")
            if user_input.lower() in ['exit', 'quit']:
                break
            result = eval(read(user_input), env)
            if result is not None:
                print(result)
        except Exception as e:
            print(f"Error: {str(e)}")
            traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        with open(sys.argv[1], 'r') as file:
            program = file.read()
        run_program(program)
    else:
        print("Lisp Interpreter REPL")
        print("Type 'exit' or 'quit' to end the session")
        repl()
