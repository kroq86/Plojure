import sys
import traceback
from functools import reduce

def atom(x):
    return not isinstance(x, list)

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
        'car': lambda lst: lst[0] if lst else None,
        'cdr': lambda lst: lst[1:] if lst else [],
        'cons': lambda x, y: [x] + (y if isinstance(y, list) else [y]),
        'list': lambda *args: list(args),
        'map': lambda func, lst: list(map(func, lst)),
        'filter': lambda func, lst: list(filter(func, lst)),
        'print': lambda *args: print(*args),
        't': True,
        'nil': None,
    }

def eval_expr(x, env):
    if atom(x):
        if isinstance(x, str):
            if x in env:
                result = env[x]
                return result
            try:
                result = atom_val(x)
                return result
            except ValueError:
                return x
        return x
    
    op, *args = x
    if op == 'cond':
        for condition, result in args:
            if condition == 't' or eval_expr(condition, env):
                result = eval_expr(result, env)
                return result
        return None
    elif op == 'set!':
        symbol, exp = args
        env[symbol] = eval_expr(exp, env)
        return env[symbol]
    elif op in env:
        evaluated_args = []
        for arg in args:
            evaluated_arg = eval_expr(arg, env)
            if isinstance(evaluated_arg, str):
                try:
                    evaluated_arg = atom_val(evaluated_arg)
                except ValueError:
                    pass
            evaluated_args.append(evaluated_arg)
            
        try:
            result = env[op](*evaluated_args)
            if op == 'print':
                return None  # print function already outputs
            return result
        except TypeError as e:
            raise TypeError(f"Invalid argument types for operation '{op}': {evaluated_args}") from e
    elif op == 'define':
        if isinstance(args[0], list):  # Function definition
            fname, *params = args[0]
            body = args[1]
            env[fname] = lambda *vals: eval_expr(body, {**env, **dict(zip(params, vals))})
            return fname
        else:  # Variable definition
            symbol, exp = args
            env[symbol] = eval_expr(exp, env)
            return symbol
    elif op == 'lambda':
        params, *body = args
        return lambda *vals: eval_expr(['begin'] + body, {**env, **dict(zip(params, vals))})
    elif op == 'begin':
        result = None
        for exp in args:
            result = eval_expr(exp, env)
        return result
    elif op == 'if':
        condition, true_branch, false_branch = args + ['nil'] if len(args) == 2 else args
        return eval_expr(true_branch, env) if eval_expr(condition, env) else eval_expr(false_branch, env)
    elif op == 'let':
        bindings, *body = args
        new_env = env.copy()
        for var, val in bindings:
            new_env[var] = eval_expr(val, env)
        return eval_expr(['begin'] + body, new_env)
    return None

def parse(tokens):
    if not tokens:
        raise SyntaxError('unexpected EOF')
    token = tokens.pop(0)
    if token == '(':  
        L = []
        while tokens:
            if tokens[0] == ')':
                tokens.pop(0)  # pop off ')'
                return L
            L.append(parse(tokens))
        raise SyntaxError('unexpected EOF while reading')
    elif token == ')':
        raise SyntaxError('unexpected )')
    return atom_val(token)

def tokenize(s):
    return s.replace('(', ' ( ').replace(')', ' ) ').split()

def read(s):
    return parse(tokenize(s))[0]

def atom_val(token):
    try:
        return int(token)
    except ValueError:
        try:
            return float(token)
        except ValueError:
            return token

def run_program(program, env=None):
    env = env or create_global_env()
    current_expression = []
    paren_count = 0
    
    for line in filter(None, map(str.strip, program.split('\n'))):
        if line.startswith(';'):  # Skip comments
            print(f"\n{line}")  # Print comments as section headers
            continue
            
        # Count parentheses
        paren_count += line.count('(') - line.count(')')
        current_expression.append(line)
        
        # If we have a complete expression
        if paren_count == 0 and current_expression:
            try:
                full_expr = ' '.join(current_expression)
                print(f"\nEvaluating: {full_expr}")
                tokens = tokenize(full_expr)
                parsed = parse(tokens)
                result = eval_expr(parsed, env)
                
                # Handle different types of results
                if result is not None:
                    if callable(result):
                        print(f"Defined function")
                    elif isinstance(result, str) and result in env and callable(env[result]):
                        print(f"Defined function '{result}'")
                    else:
                        print(f"Result: {result}")
                
                current_expression = []
            except Exception as e:
                print(f"Error: {e}")
                traceback.print_exc()
                current_expression = []
        elif paren_count < 0:
            print("Error: Unexpected closing parenthesis")
            current_expression = []
            paren_count = 0
    
    if current_expression:
        print("Warning: Incomplete expression at end of file")

def repl():
    env = create_global_env()
    while True:
        try:
            user_input = input("lisp> ")
            if user_input.lower() in ['exit', 'quit']:
                break
            result = eval_expr(read(user_input), env)
            if result is not None:
                print(result)
        except Exception as e:
            print(f"Error: {e}")
            traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        with open(sys.argv[1], 'r') as file:
            run_program(file.read())
    else:
        print("Lisp Interpreter REPL")
        repl()
