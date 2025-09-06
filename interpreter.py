#!/usr/bin/env python3
import sys
import re

env = {}

# custom exception to stop execution
class StopExe(Exception):
    pass

def eval_expr(expr: str):
    """evaluate math/variables or return string in relief code"""
    expr = expr.strip()
    try:
        # handle string assignment
        if (expr.startswith('"') and expr.endswith('"')) or (expr.startswith("'") and expr.endswith("'")):
            return expr[1:-1]

        # replace variable names with values from env
        for var, val in env.items():
            # whole word replacement
            expr = re.sub(rf'\b{var}\b', str(val), expr)

        return eval(expr)
    except Exception as e:
        print(f"ERROR: you messed up '{expr}' and life now gives you {e}")
        return None

def run_relief(code: str):
    match = re.search(r"when project start\s*{([\s\S]*)}", code)
    if not match:
        print("ERROR: entry point not found")
        return

    body = match.group(1).strip().splitlines()
    i = 0
    while i < len(body):
        line = body[i].strip()

        if not line:
            i += 1
            continue

        # stop() command
        if line.startswith("stop()"):
            raise StopExe()

        # assignment
        elif "=" in line and not line.startswith("if"):
            var, val = line.split("=", 1)
            var = var.strip()
            val = eval_expr(val)
            env[var] = val

        # out command
        elif line.startswith("out"):
            m = re.match(r"out\s*\(\s*(.*)\s*\)", line)
            if m:
                content = m.group(1)
                result = eval_expr(content)
                if result is not None:
                    print(result)

        # rep loop
        elif line.startswith("rep"):
            times = re.search(r"rep\s+(\d+)\s*{", line)
            if times:
                count = int(times.group(1))
                block = []
                i += 1
                while i < len(body) and "}" not in body[i]:
                    block.append(body[i])
                    i += 1
                for _ in range(count):
                    run_relief("when project start { " + "\n".join(block) + " }")

        # if statement
        elif line.startswith("if"):
            cond = re.search(r"if\s*\((.*)\)\s*{", line).group(1)
            condition_result = eval_expr(cond)
            block = []
            i += 1
            while i < len(body) and "}" not in body[i]:
                block.append(body[i])
                i += 1
            if condition_result:
                run_relief("when project start { " + "\n".join(block) + " }")

        i += 1

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("USAGE: python interpreter.py YOUR_PROJECT_HERE.relief")
        sys.exit(1)

    filename = sys.argv[1]
    with open(filename, "r") as f:
        code = f.read()
    try:
        run_relief(code)
    except StopExe:
        print("STOPPED: execution stopped by stop()")