import sys
import traceback
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Callable

@dataclass(frozen=True)
class InterpreterState:
    """Immutable state for the Lisp interpreter"""
    env: Dict[str, Any] = field(default_factory=dict)
    
    def with_binding(self, symbol: str, value: Any) -> 'InterpreterState':
        """Returns a new state with an updated binding"""
        new_env = self.env.copy()
        new_env[symbol] = value
        return InterpreterState(env=new_env)
    
    def get_binding(self, symbol: str) -> Optional[Any]:
        """Gets a binding from the environment"""
        return self.env.get(symbol)

def atom(x):
    return not isinstance(x, list)

def while_loop(cond, body):
    while eval(cond, env):
        eval(body, env)

def safe_arithmetic(op):
    """Creates a safe arithmetic function that handles None values"""
    def safe_func(*args):
        if None in args:
            return None
        try:
            return op(*args)
        except Exception as e:
            print(f"Error in arithmetic operation: {str(e)}")
            return None
    return safe_func

def create_initial_env() -> Dict[str, Any]:
    """Creates the initial environment with built-in functions"""
    return {
        '+': safe_arithmetic(lambda *args: sum(args)),
        '-': safe_arithmetic(lambda x, *args: x - sum(args)),
        '*': safe_arithmetic(lambda x, y: x * y),
        '/': safe_arithmetic(lambda x, y: x / y),
        '%': safe_arithmetic(lambda x, y: x % y),
        '<': safe_arithmetic(lambda x, y: x < y),
        '>': safe_arithmetic(lambda x, y: x > y),
        'eq': safe_arithmetic(lambda x, y: x == y),
        'append': lambda x, y: x + y if x is not None and y is not None else None,
        'car': lambda lst: lst[0] if isinstance(lst, list) and lst else None,
        'cdr': lambda lst: lst[1:] if isinstance(lst, list) and lst else [],
        'cons': lambda x, y: [x] + (y if isinstance(y, list) else [y]) if x is not None and y is not None else None,
        'list': lambda *args: list(args) if None not in args else None,
        'map': lambda func, lst: [func(x) for x in lst] if func is not None and lst is not None and None not in lst else None,
        'filter': lambda func, lst: [x for x in lst if func(x)] if func is not None and lst is not None and None not in lst else None,
        'print': lambda *args: print(*[arg if not callable(arg) else "<function>" for arg in args]),
        'quotient': safe_arithmetic(lambda x, y: x // y),  # Integer division for is-power-of-two
    }

def make_recursive_func(name: str, params: list, body: list, state: InterpreterState):
    """Helper function to create recursive functions"""
    def func(*vals):
        # Create new bindings for parameters
        func_state = state
        for param, val in zip(params, vals):
            func_state = func_state.with_binding(param, val)
        # Make sure the function can see itself for recursion
        func_state = func_state.with_binding(name, func)
        # Evaluate the body with access to the function itself
        result, _ = eval_expr(['begin'] + body, func_state)
        return result
    return func

def eval_expr(x: Any, state: InterpreterState) -> tuple[Any, InterpreterState]:
    """Pure function to evaluate a Lisp expression, returning the result and new state"""
    try:
        if atom(x):
            if x == 'nil':
                return False, state
            if isinstance(x, str):
                value = state.get_binding(x)
                return value if value is not None else x, state
            return x, state

        op, *args = x
        if op == 'define':
            if isinstance(args[0], list):  # Function definition (define (name params...) body...)
                name = args[0][0]
                params = args[0][1:]
                body = args[1:]
                new_func = make_recursive_func(name, params, body, state)
                new_state = state.with_binding(name, new_func)
                return None, new_state
            else:  # Variable or lambda definition
                symbol, exp = args
                if isinstance(exp, list) and exp[0] == 'lambda':
                    # Handle (define name (lambda (params) body))
                    params = exp[1]
                    body = exp[2:]
                    new_func = make_recursive_func(symbol, params, body, state)
                    new_state = state.with_binding(symbol, new_func)
                    return None, new_state
                else:
                    # Regular variable definition
                    value, new_state = eval_expr(exp, state)
                    return None, new_state.with_binding(symbol, value)
                
        elif op == 'lambda':
            params, *body = args
            def make_lambda(captured_state):
                def func(*vals):
                    # Create new bindings for parameters
                    func_state = captured_state
                    for param, val in zip(params, vals):
                        func_state = func_state.with_binding(param, val)
                    result, _ = eval_expr(['begin'] + body, func_state)
                    return result
                return func
            return make_lambda(state), state
            
        elif op == 'if':
            condition, true_branch, false_branch = args if len(args) == 3 else (*args, 'nil')
            cond_result, new_state = eval_expr(condition, state)
            branch = true_branch if cond_result else false_branch
            return eval_expr(branch, new_state)
            
        elif op == 'cond':
            for clause in args:
                if clause[0] == 't' or eval_expr(clause[0], state)[0]:
                    return eval_expr(['begin'] + clause[1:], state)
            return None, state
            
        elif op == 'let':
            bindings, *body = args
            new_state = state
            for symbol, value in bindings:
                val, new_state = eval_expr(value, new_state)
                new_state = new_state.with_binding(symbol, val)
            return eval_expr(['begin'] + body, new_state)
            
        elif op == 'begin':
            result = None
            new_state = state
            for exp in args:
                result, new_state = eval_expr(exp, new_state)
            return result, new_state
            
        elif op == 'set!':
            symbol, value = args
            if symbol not in state.env:
                raise NameError(f"Attempting to set undefined variable '{symbol}'")
            val, new_state = eval_expr(value, state)
            return val, new_state.with_binding(symbol, val)
            
        else:  # Function application
            proc, proc_state = eval_expr(op, state)
            if not callable(proc):
                raise TypeError(f"Attempted to call non-callable object '{proc}'")
            values = []
            current_state = proc_state
            for arg in args:
                val, current_state = eval_expr(arg, current_state)
                values.append(val)
            try:
                result = proc(*values)
                return result, current_state
            except Exception as e:
                print(f"Error in function application: {str(e)}")
                traceback.print_exc()
                return None, current_state
            
    except Exception as e:
        print(f"Error: {str(e)}")
        print("Traceback:")
        traceback.print_exc()
        return None, state

def eval_function(params: list, body: list, args: tuple, state: InterpreterState) -> Any:
    """Helper function to evaluate function bodies"""
    func_state = state
    for param, arg in zip(params, args):
        func_state = func_state.with_binding(param, arg)
    result, _ = eval_expr(['begin'] + body, func_state)
    return result

def run_program(program: str, state: Optional[InterpreterState] = None) -> InterpreterState:
    """Runs a Lisp program, returning the final state"""
    if state is None:
        state = InterpreterState(env=create_initial_env())
    
    current_expr = ""
    paren_count = 0
    final_state = state
    
    for line in program.split('\n'):
        line = line.strip()
        if not line or line.startswith(';'):
            continue
        current_expr += " " + line
        paren_count += line.count('(') - line.count(')')
        
        if paren_count == 0 and current_expr.strip():
            try:
                result, final_state = eval_expr(read(current_expr), final_state)
                # Print non-None results that aren't from print statements
                if result is not None and not (
                    isinstance(current_expr, str) and 
                    current_expr.strip().startswith('(print')):
                    print("Result:", result)
            except Exception as e:
                print(f"Error in expression '{current_expr}': {str(e)}")
            current_expr = ""
            
    return final_state

def repl(state: Optional[InterpreterState] = None):
    """Interactive REPL with immutable state threading"""
    if state is None:
        state = InterpreterState(env=create_initial_env())
        
    print("Lisp Interpreter REPL")
    print("Type 'exit' or 'quit' to end the session")
    
    current_state = state
    while True:
        try:
            user_input = input("lisp> ")
            if user_input.lower() in ['exit', 'quit']:
                break
            result, current_state = eval_expr(read(user_input), current_state)
            if result is not None:
                print(result)
        except Exception as e:
            print(f"Error: {str(e)}")
            traceback.print_exc()

def parse(tokens):
    """Parse a list of tokens into a Lisp expression"""
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
    """Convert a string into a list of tokens"""
    return s.replace('(', ' ( ').replace(')', ' ) ').split()

def read(s):
    """Read a string into a Lisp expression"""
    return parse(tokenize(s))

def atom_val(token):
    """Convert a token into its atomic value"""
    if token == 'nil': return False
    if token == 't': return True
    try:
        return int(token)
    except ValueError:
        try:
            return float(token)
        except ValueError:
            return str(token)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        with open(sys.argv[1], 'r') as file:
            program = file.read()
        run_program(program)
    else:
        repl()
