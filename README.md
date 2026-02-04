# pynix.sh

**pynix** is a Python-powered, cross-platform shell.
The language is a superset of Python 3 with seamless shell command integration.

<table>
<tr>
<td> <b>pynix is the Shell</b> </td>
<td> <b>pynix is Python</b> </td>
</tr>
<tr>
<td>

```bash
cd ~

whoami > /tmp/user.txt

cat /etc/passwd | grep root

ls -la
```

</td>
<td>

```python
2 + 2

var = "hello".upper()

import json
json.loads('{"a":1}')

[i for i in range(0, 10)]
```

</td>
</tr>
</table>

<table>
<tr>
<td> <b>pynix is the Shell in Python</b> </td>
<td> <b>pynix is Python in the Shell</b> </td>
</tr>
<tr>
<td>

```python
len($(curl -L https://example.com))

result = !(ls /tmp)
print(result.returncode)

x = $(whoami)
echo "User: @(x)"
```

</td>
<td>

```python
name = 'mosalah'
echo @(name) > /tmp/@(name)

files = ["a", "b", "c"]
for f in files:
    $(touch @(f).txt)

def greet(name):
    return f"Hello, {name}!"
echo @(greet("world"))
```

</td>
</tr>
</table>

If you like pynix, ⭐ the repo!

## First steps

**Installation:**

```bash
pip install pynix.sh
```

**Launch:**

```bash
pynix
```

## Builtins

| Command | Description |
|---------|-------------|
| `cd` | Change directory |
| `pwd` | Print working directory |
| `echo` | Print arguments |
| `type` | Show command type |
| `history` | Show command history |
| `exit` | Exit the shell |
| `about` | Display help for builtins |
| `activate` | Activate Python virtualenv |
| `deactivate` | Deactivate virtualenv |

## Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `@(expr)` | Expand Python expression | `echo @(2 + 2)` → `echo 4` |
| `$(cmd)` | Capture stdout | `x = $(whoami)` |
| `!(cmd)` | Capture CommandResult | `r = !(ls); print(r.returncode)` |
| `&&` | Run if previous succeeded | `true && echo yes` |
| `\|\|` | Run if previous failed | `false \|\| echo no` |
| `;` | Sequential execution | `x = 1; echo @(x)` |
| `\|` | Pipe | `echo hi \| grep h` |


## Contributing

We welcome contributors! The codebase is small and focused. Start with:

- Running the test suite: `python -m unittest discover -s tests`
- Reading the architecture in `app/core/`
- Report bugs, suggest features

## License

MIT

