import sys
import traceback


# Lisp interpreter functions
def atom(x):
    return not isinstance(x, list)


eq = lambda x, y: x == y
car = lambda x: x[0] if x else None
cdr = lambda x: x[1:] if x else None
cons = lambda x, y: [x] + (y if isinstance(y, list) else [y])
append = lambda x, y: x + y


def eval(x, env):
    try:
        if atom(x):
            if x == 'nil':
                return False
            return env.get(x, x)
        op, *args = x
        if op == 'quote':
            return args[0]
        elif op == 'define':
            symbol, exp = args
            env[symbol] = eval(exp, env)
            return symbol
        elif op == 'lambda':
            params, *body = args
            return lambda *args: eval(['begin'] + body,
                                      dict(zip(params, args), **env))
        elif op == 'begin':
            for exp in args[:-1]:
                eval(exp, env)
            return eval(args[-1], env)
        elif op == 'cond':
            for clause in args:
                if clause[0] == 't' or eval(clause[0], env):
                    return eval(['begin'] + clause[1:], env)
            return None  # If no condition is met
        elif op == 'eq':
            return eq(eval(args[0], env), eval(args[1], env))
        elif op in ['+', '-', '*', '/', '%', '<', '>']:
            values = [eval(arg, env) for arg in args]
            if op == '+': return sum(values)
            if op == '-': return values[0] - sum(values[1:])
            if op == '*': return values[0] * values[1]
            if op == '/': return values[0] / values[1]
            if op == '%': return values[0] % values[1]
            if op == '<': return values[0] < values[1]
            if op == '>': return values[0] > values[1]
        elif op == 'car':
            return car(eval(args[0], env))
        elif op == 'cdr':
            return cdr(eval(args[0], env))
        elif op == 'cons':
            return cons(eval(args[0], env), eval(args[1], env))
        elif op == 'list':
            return [eval(arg, env) for arg in args]
        elif op == 'print':
            print(*[eval(arg, env) for arg in args])
            return None
        elif op == 'read':
            return input()
        else:
            proc = eval(op, env)
            values = [eval(arg, env) for arg in args]
            return proc(*values)
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
        env = {}
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
    env = {}
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


# Main execution
if __name__ == "__main__":
    if len(sys.argv) > 1:
        with open(sys.argv[1], 'r') as file:
            program = file.read()
        run_program(program)
    else:
        print("Lisp Interpreter REPL")
        print("Type 'exit' or 'quit' to end the session")
        repl()
