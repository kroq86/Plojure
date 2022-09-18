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


def parse_word(w):
    if w == "+":
        return pls()
    elif w == "-":
        return mns()
    elif w == "=":
        return dmp()
    else:
        return mov(int(w))


def parser():
    with open("program.plj", "r") as prg:
        return [parse_word(w) for w in prg.read().split()]


program = parser()
run_program(program)
compile_program(program)  #TODO segmentation fault for printf second operation
