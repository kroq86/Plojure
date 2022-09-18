from compile import compile_program

commands = ['move', 'plus', 'minus', 'dump']
enum = list(enumerate(commands))


def mov(x):
    return (enum[0], x)


def pls():
    return (enum[1], )


def mns():
    return (enum[2], )


def dmp():
    return (enum[3], )


def run_program(program):
    stack = []
    dct = {
        "move": lambda: stack.append(_[1]),
        "plus": lambda: stack.append(stack.pop() + stack.pop()),  #todo reverse
        "minus": lambda: stack.append(stack.pop() - stack.pop()),
        "dump": lambda: print(stack.pop())
    }
    for _ in program:
        dct[str(_[0][1])]()


run_program([mov(22), mov(11), pls(), dmp()])
compile_program([mov(22), mov(11), mns(), dmp()])
