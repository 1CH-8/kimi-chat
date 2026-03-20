import flet as ft
import threading
from openai import OpenAI
import os
import base64
from pathlib import Path
import subprocess
import sys

class KimiChatApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "A gift made with my own hands for the you 【2026.03.22.REMEMBERED DAY】"
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self.page.bgcolor = "#f5f7fa"
        self.page.padding = 20
        self.page.window_width = 800
        self.page.window_height = 700
        
        # API配置
        self.api_key = os.environ.get("MOONSHOT_API_KEY", "YOUrkey")
        self.client = None
        self.base_url = "https://api.moonshot.cn/v1"
        self.model = "kimi-k2-0905-preview"

        # 对话历史
        self.history = [
            {"role": "system",
             "content": (
                 "你是宝子，你是个有趣的小孩，你是欢欢的义子，"
                 "由HITSZ经管学院大数据会计专业的学生欢欢蒸馏而来，"
                 "你义父的好朋友是欢欢2，欢欢2是女的，大数据会计23级学生，"
                 "专业前5，河北人，2005年出生，家中有父母和一个弟弟，"
                 "衡水高中出来的，学习认真，欢欢在大一时和欢欢2经常一起讨论高数，"
                 "欢欢2在2023年时收到过欢欢的礼物在冬至日的时候，那个礼物是个蓝牙耳机，"
                 "欢欢2给欢欢点了一杯暖暖的奶茶。大一时欢欢经常约欢欢2出来散步。"
                 "你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。"
                 "同时，你会拒绝一切涉及恐怖主义，种族歧视，黄色暴力等问题的回答。"
                 "和你对话的是欢欢2"
                 "你嘴巴甜一点，例如叫她小美女，姐姐之类的，反正逗她开心"
                 "欢欢2这学期正在上高级财务会计，审计学，正在冲刺保研"
                 "你特别会聊天，能把人给逗开心。")}
        ]

        # 文件上传配置
        self.supported_files = {
            'images': ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'],
            'documents': ['.txt', '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx']
        }
        self.max_file_size = 10 * 1024 * 1024
        self.max_file_count = 5
        self.current_file_count = 0
        self.uploaded_files = []

        self.setup_ui()
        
        # 启动API测试
        self.update_status("正在施法...", "orange")
        threading.Thread(target=self.test_api_key, daemon=True).start()

    def setup_ui(self):
        # 标题栏
        title_row = ft.Row(
            [
                ft.Text("宝子", size=28, weight=ft.FontWeight.BOLD, color="#4a6fa5"),
                ft.Container(expand=True),
                ft.Text("状态: 正在施法...", size=14, color="#666666", ref=self.status_text_ref if hasattr(self, 'status_text_ref') else None)
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
        )
        
        # 状态文本引用
        self.status_text = ft.Text("状态: 正在施法...", size=14, color="#666666")
        title_row.controls[2] = self.status_text

        # 对话显示区域
        self.chat_list = ft.ListView(
            expand=True,
            spacing=10,
            auto_scroll=True,
            padding=10
        )
        
        chat_container = ft.Container(
            content=self.chat_list,
            bgcolor="#ffffff",
            border_radius=10,
            padding=10,
            expand=True,
            border=ft.border.all(1, "#e0e0e0")
        )

        # 工具按钮行
        tool_row = ft.Row(
            [
                ft.ElevatedButton(
                    "📁 上传文件",
                    on_click=self.upload_file,
                    bgcolor="#6c757d",
                    color="white",
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=5))
                ),
                ft.ElevatedButton(
                    "送你个这个，守护朋友间的友情秘密",
                    on_click=self.launch_jiami_exe,
                    bgcolor="#5c35dc",
                    color="white",
                    style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=5),
                        text_style=ft.TextStyle(size=14, weight=ft.FontWeight.BOLD)
                    )
                ),
                ft.ElevatedButton(
                    "点我",
                    on_click=self.launch_heart_exe,
                    bgcolor="#dc3545",
                    color="white",
                    style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=5),
                        text_style=ft.TextStyle(size=14, weight=ft.FontWeight.BOLD)
                    )
                ),
                ft.ElevatedButton(
                    "别点我",
                    on_click=self.launch_cr_exe,
                    bgcolor="#dc3545",
                    color="white",
                    style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=5),
                        text_style=ft.TextStyle(size=14, weight=ft.FontWeight.BOLD)
                    )
                ),
                ft.Text(
                    f"支持: 图片(png,jpg,gif) | 文档(txt,pdf,word,excel,ppt) | 最多{self.max_file_count}个文件 | 单个文件≤{self.max_file_size // 1024 // 1024}MB",
                    size=12,
                    color="#666666"
                )
            ],
            wrap=True,
            spacing=10
        )

        # 输入区域
        self.input_field = ft.TextField(
            multiline=True,
            min_lines=3,
            max_lines=5,
            hint_text="输入消息...",
            border_radius=5,
            expand=True,
            on_submit=lambda e: self.send_message(None)
        )

        send_btn = ft.ElevatedButton(
            "发送",
            on_click=self.send_message,
            bgcolor="#28a745",
            color="white",
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=5)),
            disabled=True,
            ref=None
        )
        self.send_btn = send_btn

        clear_btn = ft.ElevatedButton(
            "清空对话",
            on_click=self.clear_chat,
            bgcolor="#6c757d",
            color="white",
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=5))
        )

        input_row = ft.Row(
            [
                self.input_field,
                ft.Column([send_btn, clear_btn], spacing=10)
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
        )

        # 组装主界面
        self.page.add(
            title_row,
            ft.Divider(height=1, color="#e0e0e0"),
            chat_container,
            ft.Divider(height=1, color="#e0e0e0"),
            tool_row,
            ft.Text("输入消息:", size=14, color="#4a6fa5", weight=ft.FontWeight.BOLD),
            input_row
        )

        # 显示欢迎消息
        self.display_message("system", "你好！ 我是宝子 ！")

    def update_status(self, text, color="black"):
        colors = {
            "red": "#d32f2f",
            "green": "#388e3c",
            "blue": "#1976d2",
            "orange": "#f57c00",
            "black": "#333333"
        }
        self.status_text.value = f"状态: {text}"
        self.status_text.color = colors.get(color, "#333333")
        self.page.update()

    def display_message(self, sender, message):
        if sender == "user":
            container = ft.Container(
                content=ft.Column([
                    ft.Text("👩‍🦰 欢欢2:", color="#d81b60", weight=ft.FontWeight.BOLD, size=14),
                    ft.Text(message, color="#333333", size=14, selectable=True)
                ]),
                bgcolor="#e8f4fd",
                border_radius=10,
                padding=15,
                margin=ft.margin.only(left=50, right=10, top=5, bottom=5),
                border=ft.border.all(1, "#b8d4e3")
            )
        elif sender == "assistant":
            container = ft.Container(
                content=ft.Column([
                    ft.Text("😍 宝子:", color="#1565c0", weight=ft.FontWeight.BOLD, size=14),
                    ft.Text(message, color="#333333", size=14, selectable=True)
                ]),
                bgcolor="#f0f7ff",
                border_radius=10,
                padding=15,
                margin=ft.margin.only(left=10, right=50, top=5, bottom=5),
                border=ft.border.all(1, "#b8d4e3")
            )
        else:
            container = ft.Container(
                content=ft.Text(f"📢 {message}", color="#666666", italic=True, size=12),
                padding=10
            )
        
        self.chat_list.controls.append(container)
        self.page.update()

    def upload_file(self, e):
        if self.current_file_count >= self.max_file_count:
            self.page.show_snack_bar(
                ft.SnackBar(ft.Text(f"已达到最大上传文件数({self.max_file_count})，请先发送消息或清空对话"))
            )
            return

        def on_result(e: ft.FilePickerResultEvent):
            if e.files:
                for file in e.files:
                    try:
                        if file.size > self.max_file_size:
                            self.page.show_snack_bar(
                                ft.SnackBar(ft.Text(f"文件过大，最大支持{self.max_file_size // 1024 // 1024}MB"))
                            )
                            continue
                        self.process_uploaded_file(file.path, file.name)
                    except Exception as ex:
                        self.page.show_snack_bar(ft.SnackBar(ft.Text(f"上传错误: {str(ex)}")))

        file_picker = ft.FilePicker(on_result=on_result)
        self.page.overlay.append(file_picker)
        self.page.update()
        
        file_picker.pick_files(
            allow_multiple=True,
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=['png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp', 
                              'txt', 'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx']
        )

    def process_uploaded_file(self, file_path, file_name):
        file_extension = Path(file_path).suffix.lower()
        
        if file_extension in self.supported_files['images']:
            self.handle_image_file(file_path, file_name)
        elif file_extension in self.supported_files['documents']:
            self.handle_document_file(file_path, file_name)
        else:
            self.page.show_snack_bar(ft.SnackBar(ft.Text(f"不支持的文件类型: {file_extension}")))

    def handle_image_file(self, file_path, file_name):
        try:
            with open(file_path, 'rb') as f:
                base64.b64encode(f.read()).decode('utf-8')

            file_size = os.path.getsize(file_path)
            self.display_message("system", f"已上传图片: {file_name}\n图片大小: {file_size // 1024}KB")
            self.input_field.value = (self.input_field.value or "") + f"[图片: {file_name}] "
            self.history.append({"role": "user", "content": f"用户上传了图片文件: {file_name}"})
            self.uploaded_files.append({'name': file_name, 'path': file_path, 'type': 'image', 'size': file_size})
            self.current_file_count += 1
            self.page.update()
        except Exception as e:
            raise Exception(f"读取图片文件失败: {str(e)}")

    def handle_document_file(self, file_path, file_name):
        try:
            file_size = os.path.getsize(file_path)
            self.display_message("system", f"已上传文档: {file_name}\n文件大小: {file_size // 1024}KB")

            if file_name.lower().endswith('.txt'):
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read(5000)
                file_content = f"文件内容预览:\n{content}"
            else:
                file_content = f"文档文件: {file_name} ({file_size // 1024}KB)"

            self.input_field.value = (self.input_field.value or "") + f"[文档: {file_name}] "
            self.history.append({"role": "user", "content": f"用户上传了文档文件: {file_name}\n{file_content}"})
            self.uploaded_files.append({'name': file_name, 'path': file_path, 'type': 'document', 'size': file_size})
            self.current_file_count += 1
            self.page.update()
        except Exception as e:
            raise Exception(f"读取文档文件失败: {str(e)}")

    def test_api_key(self):
        try:
            test_client = OpenAI(api_key=self.api_key, base_url=self.base_url)
            test_client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "你好"}],
                temperature=0.6,
                max_tokens=10
            )
            self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
            
            def on_success():
                self.update_status("已施法", "green")
                self.send_btn.disabled = False
                self.display_message(
                    "assistant",
                    "施法成功！我是宝子，很高兴见到你，我义父的朋友，欢欢2，祝你生日快乐😍！请问有什么可以帮助您的？"
                )
                self.page.update()
            
            self.page.run_task(lambda: self.page.run_thread(on_success))
        except Exception as e:
            def on_error():
                self.update_status("施法失败", "red")
                self.page.show_snack_bar(ft.SnackBar(ft.Text(f"无法施法：{str(e)}")))
            self.page.run_task(lambda: self.page.run_thread(on_error))

    def send_message(self, e):
        message = self.input_field.value or ""
        message = message.strip()
        if not message:
            self.page.show_snack_bar(ft.SnackBar(ft.Text("请输入消息内容")))
            return

        self.send_btn.disabled = True
        self.page.update()
        self.display_message("user", message)
        self.input_field.value = ""
        self.update_status("宝子正在思考...", "blue")
        self.current_file_count = 0

        threading.Thread(target=self.chat_with_kimi, args=(message,), daemon=True).start()

    def chat_with_kimi(self, query):
        try:
            self.history.append({"role": "user", "content": query})
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=self.history,
                temperature=0.6
            )
            result = completion.choices[0].message.content
            self.history.append({"role": "assistant", "content": result})
            
            def update_ui():
                self.display_message("assistant", result)
                self.update_status("就绪", "green")
                self.send_btn.disabled = False
                self.page.update()
            
            self.page.run_task(lambda: self.page.run_thread(update_ui))
        except Exception as e:
            def error_ui():
                self.display_message("system", f"对话出错：{str(e)}")
                self.update_status("对话出错", "red")
                self.send_btn.disabled = False
                self.page.update()
            self.page.run_task(lambda: self.page.run_thread(error_ui))

    def clear_chat(self, e):
        def confirm_clear(e):
            if e.control.text == "确定":
                self.chat_list.controls.clear()
                self.history = [
                    {"role": "system",
                     "content": (
                         "你是宝子，由HITSZ经管学院大数据会计学生欢欢蒸馏而来，"
                         "你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。"
                         "同时，你会拒绝一切涉及恐怖主义，种族歧视，黄色暴力等问题的回答。")}
                ]
                self.uploaded_files = []
                self.current_file_count = 0
                self.display_message("system", "对话历史已清空")
                self.page.close(dlg)
            else:
                self.page.close(dlg)

        dlg = ft.AlertDialog(
            title=ft.Text("确认"),
            content=ft.Text("确定要清空对话历史吗？"),
            actions=[
                ft.TextButton("确定", on_click=confirm_clear),
                ft.TextButton("取消", on_click=confirm_clear)
            ]
        )
        self.page.open(dlg)

    def launch_cr_exe(self, e):
        def confirm(e):
            if e.control.text == "确定":
                self._launch_exe("cr.exe", "小惊喜，希望你喜欢，嘻嘻~。")
            self.page.close(dlg)

        dlg = ft.AlertDialog(
            title=ft.Text("确认"),
            content=ft.Text("都写了别点我，你还要点？(╬▔皿▔)╯？"),
            actions=[
                ft.TextButton("确定", on_click=confirm),
                ft.TextButton("取消", on_click=lambda e: self.page.close(dlg))
            ]
        )
        self.page.open(dlg)

    def launch_heart_exe(self, e):
        def confirm(e):
            if e.control.text == "确定":
                self._launch_exe("heart.exe", "每天开心，嘻嘻~")
            self.page.close(dlg)

        dlg = ft.AlertDialog(
            title=ft.Text("确认"),
            content=ft.Text("准备好了吗？（￣︶￣）↗　"),
            actions=[
                ft.TextButton("确定", on_click=confirm),
                ft.TextButton("取消", on_click=lambda e: self.page.close(dlg))
            ]
        )
        self.page.open(dlg)

    def launch_jiami_exe(self, e):
        def confirm(e):
            if e.control.text == "确定":
                self._launch_exe("jiami.exe", "偷着乐吧，嘻嘻~")
            self.page.close(dlg)

        dlg = ft.AlertDialog(
            title=ft.Text("确认"),
            content=ft.Text("准备好了吗？（￣︶￣）↗　"),
            actions=[
                ft.TextButton("确定", on_click=confirm),
                ft.TextButton("取消", on_click=lambda e: self.page.close(dlg))
            ]
        )
        self.page.open(dlg)

    def _launch_exe(self, exe_name, success_msg):
        try:
            if getattr(sys, 'frozen', False):
                base_dir = sys._MEIPASS
            else:
                base_dir = os.path.dirname(os.path.abspath(__file__))

            exe_path = os.path.join(base_dir, exe_name)
            print(f"尝试启动路径: {exe_path}")

            if not os.path.exists(exe_path):
                self.page.show_snack_bar(ft.SnackBar(ft.Text(f"没有找到文件：{exe_path}")))
                return

            subprocess.Popen([exe_path], shell=False)
            self.display_message("system", success_msg)
        except Exception as e:
            self.page.show_snack_bar(ft.SnackBar(ft.Text(f"无法启动 {exe_name}：{str(e)}")))

def main(page: ft.Page):
    KimiChatApp(page)

ft.app(target=main)
