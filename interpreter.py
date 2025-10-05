#!/usr/bin/env python3
import sys
import re
import time

env = {}

class StopExe(Exception):
    pass

def eval_expr(expr: str):
    expr = expr.strip()
    try:
        if (expr.startswith('"') and expr.endswith('"')) or (expr.startswith("'") and expr.endswith("'")):
            return expr[1:-1]

        m = re.match(r'in\s*\(\s*"(.*)"\s*\)', expr)
        if m:
            prompt = m.group(1)
            return input(prompt + " ")

        def replacer(match):
            var = match.group(0)
            if var in env:
                val = env[var]
                if isinstance(val, str):
                    return f'"{val}"'
                else:
                    return str(val)
            return var

        expr = re.sub(r'\b[A-Za-z_][A-Za-z0-9_]*\b', replacer, expr)

        try:
            result = eval(expr)
            return result
        except Exception as e:
            print(f"ERROR: {e} from '{expr}'")
            return None
    except Exception as e:
        print(f"ERROR: {e} from '{expr}'")
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

        if line.startswith("stop()"):
            raise StopExe()

        elif line.startswith("wait."):
            m = re.match(r"wait\.(\w+)\((\d+)\)", line)
            if m:
                unit, value = m.groups()
                value = int(value)
                if unit == "milsec":
                    time.sleep(value / 1000.0)
                elif unit == "sec":
                    time.sleep(value)
                elif unit == "min":
                    time.sleep(value * 60)
                elif unit == "hrs":
                    time.sleep(value * 3600)
                else:
                    print(f"ERROR: unknown '{unit}'")

        elif "=" in line and not line.startswith("if"):
            var, val = line.split("=", 1)
            var = var.strip()

            if not re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', var):
                print(f"ERROR: invalid variable name '{var}'")
                i += 1
                continue

            val = eval_expr(val)
            env[var] = val

        elif line.startswith("out"):
            m = re.match(r"out\s*\(\s*(.*)\s*\)", line)
            if m:
                content = m.group(1)
                result = eval_expr(content)
                if result is not None:
                    print(result)

        elif line.startswith("in"):
            m = re.match(r'in\s*\(\s*"(.*)"\s*\)', line)
            if m:
                prompt = m.group(1)
                user_input = input(prompt + " ")
                env["_last_input"] = user_input

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
            else:
                print(f"ERROR: invalid rep syntax in line {line}")

        elif line.startswith("if"):
            m = re.search(r"if\s*\((.*)\)\s*{", line)
            if m:
                cond = m.group(1)
                condition_result = eval_expr(cond)
                block = []
                i += 1
                while i < len(body) and "}" not in body[i]:
                    block.append(body[i])
                    i += 1

                if condition_result:
                    run_relief("when project start { " + "\n".join(block) + " }")
                else:
                    i += 1
                    while i < len(body):
                        next_line = body[i].strip()

                        if next_line.startswith("else if"):
                            m = re.search(r"else if\s*\((.*)\)\s*{", next_line)
                            if m:
                                cond = m.group(1)
                                condition_result = eval_expr(cond)
                                block = []
                                i += 1
                                while i < len(body) and "}" not in body[i]:
                                    block.append(body[i])
                                    i += 1

                                if condition_result:
                                    run_relief("when project start { " + "\n".join(block) + " }")
                                    break

                        elif next_line.startswith("else"):
                            block = []
                            i += 1
                            while i < len(body) and "}" not in body[i]:
                                block.append(body[i])
                                i += 1

                            run_relief("when project start { " + "\n".join(block) + " }")
                            break

                        i += 1
            else:
                print(f"ERROR: invalid if syntax in line {line}")

        elif line.startswith("defy"):
            m = re.match(r"defy\s*\(\s*(\w+)\s*\)\s*{", line)
            if m:
                func_name = m.group(1)
                block = []
                i += 1
                while i < len(body) and "}" not in body[i]:
                    block.append(body[i])
                    i += 1
                env[func_name] = block
            else:
                print(f"ERROR: invalid defy syntax in line {line}")

        elif re.match(r"\w+\(\)", line):
            func_name = line.split("(")[0].strip()
            if func_name in env:
                func_body = env[func_name]
                run_relief("when project start { " + "\n".join(func_body) + " }")
            else:
                print(f"ERROR: undefined function '{func_name}'")

        i += 1

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("USAGE: relief YOUR_PROJECT_HERE.relief")
        sys.exit(1)

    filename = sys.argv[1]
    with open(filename, "r") as f:
        code = f.read()
    try:
        run_relief(code)
    except StopExe:
        print("STOPPED: execution stopped by stop()")
