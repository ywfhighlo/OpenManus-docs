# 字符串替换编辑器模块
# 设计说明：
# 1. 提供文件查看和编辑功能
# 2. 支持字符串替换和插入操作
# 3. 实现编辑历史和撤销功能
# 4. 提供文件内容截断处理

from collections import defaultdict
from pathlib import Path
from typing import Literal, get_args

from app.exceptions import ToolError
from app.tool import BaseTool
from app.tool.base import CLIResult, ToolResult
from app.tool.run import run


# 命令类型定义
Command = Literal[
    "view",      # 查看文件内容
    "create",    # 创建新文件
    "str_replace", # 字符串替换
    "insert",    # 插入内容
    "undo_edit", # 撤销编辑
]

# 配置常量
SNIPPET_LINES: int = 4  # 代码片段显示行数
MAX_RESPONSE_LEN: int = 16000  # 最大响应长度
TRUNCATED_MESSAGE: str = "<response clipped><NOTE>To save on context only part of this file has been shown to you. You should retry this tool after you have searched inside the file with `grep -n` in order to find the line numbers of what you are looking for.</NOTE>"

# 工具描述
_STR_REPLACE_EDITOR_DESCRIPTION = """Custom editing tool for viewing, creating and editing files
* State is persistent across command calls and discussions with the user
* If `path` is a file, `view` displays the result of applying `cat -n`. If `path` is a directory, `view` lists non-hidden files and directories up to 2 levels deep
* The `create` command cannot be used if the specified `path` already exists as a file
* If a `command` generates a long output, it will be truncated and marked with `<response clipped>`
* The `undo_edit` command will revert the last edit made to the file at `path`

Notes for using the `str_replace` command:
* The `old_str` parameter should match EXACTLY one or more consecutive lines from the original file. Be mindful of whitespaces!
* If the `old_str` parameter is not unique in the file, the replacement will not be performed. Make sure to include enough context in `old_str` to make it unique
* The `new_str` parameter should contain the edited lines that should replace the `old_str`
"""


def maybe_truncate(content: str, truncate_after: int | None = MAX_RESPONSE_LEN):
    """
    Truncate content and append a notice if content exceeds the specified length.
    
    内容截断处理
    
    功能：
    1. 长度检查：检查内容是否超过限制
    2. 截断处理：超出限制时进行截断
    3. 提示添加：添加截断提示信息
    """
    return (
        content
        if not truncate_after or len(content) <= truncate_after
        else content[:truncate_after] + TRUNCATED_MESSAGE
    )


class StrReplaceEditor(BaseTool):
    """
    A tool for executing bash commands
    
    字符串替换编辑器
    功能特性：
    1. 文件操作：查看、创建、编辑文件
    2. 字符串处理：替换和插入操作
    3. 历史管理：支持编辑历史和撤销
    4. 路径验证：确保路径有效性
    """

    name: str = "str_replace_editor"
    description: str = _STR_REPLACE_EDITOR_DESCRIPTION
    # 工具参数定义
    # 包括：
    # - command: 执行的命令类型
    # - path: 文件或目录的路径
    # - file_text: 创建文件的内容
    # - old_str: 要替换的字符串
    # - new_str: 新的字符串
    # - insert_line: 插入位置
    # - view_range: 查看范围
    parameters: dict = {
        "type": "object",
        "properties": {
            "command": {
                "description": "The commands to run. Allowed options are: `view`, `create`, `str_replace`, `insert`, `undo_edit`.",
                "enum": ["view", "create", "str_replace", "insert", "undo_edit"],
                "type": "string",
            },
            "path": {
                "description": "Absolute path to file or directory.",
                "type": "string",
            },
            "file_text": {
                "description": "Required parameter of `create` command, with the content of the file to be created.",
                "type": "string",
            },
            "old_str": {
                "description": "Required parameter of `str_replace` command containing the string in `path` to replace.",
                "type": "string",
            },
            "new_str": {
                "description": "Optional parameter of `str_replace` command containing the new string (if not given, no string will be added). Required parameter of `insert` command containing the string to insert.",
                "type": "string",
            },
            "insert_line": {
                "description": "Required parameter of `insert` command. The `new_str` will be inserted AFTER the line `insert_line` of `path`.",
                "type": "integer",
            },
            "view_range": {
                "description": "Optional parameter of `view` command when `path` points to a file. If none is given, the full file is shown. If provided, the file will be shown in the indicated line number range, e.g. [11, 12] will show lines 11 and 12. Indexing at 1 to start. Setting `[start_line, -1]` shows all lines from `start_line` to the end of the file.",
                "items": {"type": "integer"},
                "type": "array",
            },
        },
        "required": ["command", "path"],
    }

    # 文件历史记录
    _file_history: list = defaultdict(list)

    async def execute(
        self,
        *,
        command: Command,
        path: str,
        file_text: str | None = None,
        view_range: list[int] | None = None,
        old_str: str | None = None,
        new_str: str | None = None,
        insert_line: int | None = None,
        **kwargs,
    ) -> str:
        """
        Execute the editor command with the given parameters.
        
        执行编辑器命令
        
        功能：
        1. 路径验证：检查路径有效性
        2. 命令分发：根据命令类型调用相应方法
        3. 参数验证：确保必要参数存在
        4. 结果处理：统一的结果返回格式
        """
        _path = Path(path)
        self.validate_path(command, _path)
        if command == "view":
            result = await self.view(_path, view_range)
        elif command == "create":
            if file_text is None:
                raise ToolError("Parameter `file_text` is required for command: create")
            self.write_file(_path, file_text)
            self._file_history[_path].append(file_text)
            result = ToolResult(output=f"File created successfully at: {_path}")
        elif command == "str_replace":
            if old_str is None:
                raise ToolError(
                    "Parameter `old_str` is required for command: str_replace"
                )
            result = self.str_replace(_path, old_str, new_str)
        elif command == "insert":
            if insert_line is None:
                raise ToolError(
                    "Parameter `insert_line` is required for command: insert"
                )
            if new_str is None:
                raise ToolError("Parameter `new_str` is required for command: insert")
            result = self.insert(_path, insert_line, new_str)
        elif command == "undo_edit":
            result = self.undo_edit(_path)
        else:
            raise ToolError(
                f'Unrecognized command {command}. The allowed commands for the {self.name} tool are: {", ".join(get_args(Command))}'
            )
        return str(result)

    def validate_path(self, command: str, path: Path):
        """
        Check that the path/command combination is valid.
        
        路径验证
        
        功能：
        1. 绝对路径检查：确保是绝对路径
        2. 存在性检查：确保路径存在（除create命令外）
        3. 类型检查：确保目录只用于view命令
        """
        # Check if its an absolute path
        if not path.is_absolute():
            suggested_path = Path("") / path
            raise ToolError(
                f"The path {path} is not an absolute path, it should start with `/`. Maybe you meant {suggested_path}?"
            )
        # Check if path exists
        if not path.exists() and command != "create":
            raise ToolError(
                f"The path {path} does not exist. Please provide a valid path."
            )
        if path.exists() and command == "create":
            raise ToolError(
                f"File already exists at: {path}. Cannot overwrite files using command `create`."
            )
        # Check if the path points to a directory
        if path.is_dir():
            if command != "view":
                raise ToolError(
                    f"The path {path} is a directory and only the `view` command can be used on directories"
                )

    async def view(self, path: Path, view_range: list[int] | None = None):
        """
        Implement the view command
        
        查看文件内容
        
        功能：
        1. 目录处理：显示目录结构（最多2层）
        2. 文件处理：显示文件内容
        3. 范围控制：支持指定行范围
        4. 格式化输出：添加行号和格式化
        """
        if path.is_dir():
            if view_range:
                raise ToolError(
                    "The `view_range` parameter is not allowed when `path` points to a directory."
                )

            _, stdout, stderr = await run(
                rf"find {path} -maxdepth 2 -not -path '*/\.*'"
            )
            if not stderr:
                stdout = f"Here's the files and directories up to 2 levels deep in {path}, excluding hidden items:\n{stdout}\n"
            return CLIResult(output=stdout, error=stderr)

        file_content = self.read_file(path)
        init_line = 1
        if view_range:
            if len(view_range) != 2 or not all(isinstance(i, int) for i in view_range):
                raise ToolError(
                    "Invalid `view_range`. It should be a list of two integers."
                )
            file_lines = file_content.split("\n")
            n_lines_file = len(file_lines)
            init_line, final_line = view_range
            if init_line < 1 or init_line > n_lines_file:
                raise ToolError(
                    f"Invalid `view_range`: {view_range}. Its first element `{init_line}` should be within the range of lines of the file: {[1, n_lines_file]}"
                )
            if final_line > n_lines_file:
                raise ToolError(
                    f"Invalid `view_range`: {view_range}. Its second element `{final_line}` should be smaller than the number of lines in the file: `{n_lines_file}`"
                )
            if final_line != -1 and final_line < init_line:
                raise ToolError(
                    f"Invalid `view_range`: {view_range}. Its second element `{final_line}` should be larger or equal than its first `{init_line}`"
                )

            if final_line == -1:
                file_content = "\n".join(file_lines[init_line - 1 :])
            else:
                file_content = "\n".join(file_lines[init_line - 1 : final_line])

        return CLIResult(
            output=self._make_output(file_content, str(path), init_line=init_line)
        )

    def str_replace(self, path: Path, old_str: str, new_str: str | None):
        """
        Implement the str_replace command, which replaces old_str with new_str in the file content
        
        字符串替换
        
        功能：
        1. 内容读取：读取文件内容
        2. 唯一性检查：确保要替换的字符串唯一
        3. 替换处理：执行字符串替换
        4. 历史记录：保存修改历史
        5. 片段显示：显示修改部分的上下文
        """
        # Read the file content
        file_content = self.read_file(path).expandtabs()
        old_str = old_str.expandtabs()
        new_str = new_str.expandtabs() if new_str is not None else ""

        # Check if old_str is unique in the file
        occurrences = file_content.count(old_str)
        if occurrences == 0:
            raise ToolError(
                f"No replacement was performed, old_str `{old_str}` did not appear verbatim in {path}."
            )
        elif occurrences > 1:
            file_content_lines = file_content.split("\n")
            lines = [
                idx + 1
                for idx, line in enumerate(file_content_lines)
                if old_str in line
            ]
            raise ToolError(
                f"No replacement was performed. Multiple occurrences of old_str `{old_str}` in lines {lines}. Please ensure it is unique"
            )

        # Replace old_str with new_str
        new_file_content = file_content.replace(old_str, new_str)

        # Write the new content to the file
        self.write_file(path, new_file_content)

        # Save the content to history
        self._file_history[path].append(file_content)

        # Create a snippet of the edited section
        replacement_line = file_content.split(old_str)[0].count("\n")
        start_line = max(0, replacement_line - SNIPPET_LINES)
        end_line = replacement_line + SNIPPET_LINES + new_str.count("\n")
        snippet = "\n".join(new_file_content.split("\n")[start_line : end_line + 1])

        # Prepare the success message
        success_msg = f"The file {path} has been edited. "
        success_msg += self._make_output(
            snippet, f"a snippet of {path}", start_line + 1
        )
        success_msg += "Review the changes and make sure they are as expected. Edit the file again if necessary."

        return CLIResult(output=success_msg)

    def insert(self, path: Path, insert_line: int, new_str: str):
        """
        Insert new_str after the specified line in the file.
        
        插入内容
        
        功能：
        1. 行号验证：确保插入位置有效
        2. 内容处理：处理插入内容的格式
        3. 历史记录：保存修改历史
        4. 片段显示：显示修改部分的上下文
        """
        # Read the file content
        file_content = self.read_file(path)
        file_lines = file_content.split("\n")

        # Validate insert_line
        if insert_line < 0 or insert_line >= len(file_lines):
            raise ToolError(
                f"Invalid insert_line: {insert_line}. Must be between 0 and {len(file_lines) - 1}"
            )

        # Insert the new string after the specified line
        file_lines.insert(insert_line + 1, new_str)
        new_file_content = "\n".join(file_lines)

        # Write the new content to the file
        self.write_file(path, new_file_content)

        # Save the content to history
        self._file_history[path].append(file_content)

        # Create a snippet of the edited section
        start_line = max(0, insert_line - SNIPPET_LINES)
        end_line = insert_line + SNIPPET_LINES + 2
        snippet = "\n".join(file_lines[start_line:end_line])

        # Prepare the success message
        success_msg = f"The file {path} has been edited. "
        success_msg += self._make_output(
            snippet, f"a snippet of {path}", start_line + 1
        )
        return ToolResult(output=success_msg)

    def undo_edit(self, path: Path):
        """
        Undo the last edit made to the file.
        
        撤销编辑
        
        功能：
        1. 历史检查：确保有可撤销的历史
        2. 内容恢复：恢复到上一个版本
        3. 历史更新：移除最后一次修改记录
        """
        if not self._file_history[path]:
            raise ToolError(f"No edit history available for file: {path}")

        # Get the last version of the file
        last_version = self._file_history[path].pop()

        # Write the last version back to the file
        self.write_file(path, last_version)

        return ToolResult(
            output=f"Last edit to {path} has been undone.\n\n{self._make_output(last_version, str(path))}"
        )

    def read_file(self, path: Path):
        """
        Read the contents of a file.
        
        读取文件
        
        功能：
        1. 文件打开：使用UTF-8编码
        2. 内容读取：读取全部内容
        """
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def write_file(self, path: Path, file: str):
        """
        Write content to a file.
        
        写入文件
        
        功能：
        1. 文件打开：使用UTF-8编码
        2. 内容写入：写入全部内容
        """
        with open(path, "w", encoding="utf-8") as f:
            f.write(file)

    def _make_output(
        self,
        file_content: str,
        file_descriptor: str,
        init_line: int = 1,
        expand_tabs: bool = True,
    ):
        """
        Format file content for display.
        
        格式化输出
        
        功能：
        1. 内容处理：处理制表符
        2. 行号添加：添加行号前缀
        3. 长度控制：截断过长内容
        4. 描述信息：添加文件描述
        """
        if expand_tabs:
            file_content = file_content.expandtabs()

        # Add line numbers
        lines = file_content.split("\n")
        max_line_num_width = len(str(init_line + len(lines) - 1))
        numbered_lines = []
        for i, line in enumerate(lines, init_line):
            line_num = str(i).rjust(max_line_num_width)
            numbered_lines.append(f"{line_num} | {line}")
        numbered_content = "\n".join(numbered_lines)

        # Truncate if necessary and return
        return maybe_truncate(
            f"Here's the content of {file_descriptor}:\n{numbered_content}\n"
        )
