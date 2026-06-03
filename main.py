import os
import sys
import threading
import subprocess
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.relativelayout import RelativeLayout
from kivy.graphics import Color, RoundedRectangle, Line
from kivy.animation import Animation 
from kivy.properties import ListProperty 
from kivy.core.window import Window

# Подключение Java-инструментов Android для работы с системным VPN
if sys.platform == 'android':
    from jnius import autoclass
    from android import activity

Window.size = (360, 640)
Window.clearcolor = (0.07, 0.07, 0.09, 1)

LIST_FILE = "bypass_list.txt"

BYPASS_SETTINGS = {
    "mode": "auto",           
    "custom_ip": "185.22.15.44",
    "custom_port": "9999",
    "split_size": "2",  
    "domains": "youtube.com\ngooglevideo.com\nyoutu.be\ndiscord.com\ndiscordapp.com"
}

proxy_running = False
bye_dpi_process = None

def load_domains_from_file():
    if os.path.exists(LIST_FILE):
        try:
            with open(LIST_FILE, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content: 
                    BYPASS_SETTINGS["domains"] = content
        except: 
            pass

class RoundedButton(Button):
    bg_color = ListProperty([0.12, 0.13, 0.18, 1])
    def __init__(self, bg_color=[0.12, 0.13, 0.18, 1], **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ''
        self.background_color = (0, 0, 0, 0)
        self.bg_color = bg_color
        self.bind(pos=self.update_canvas, size=self.update_canvas, bg_color=self.update_canvas)

    def update_canvas(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*self.bg_color)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[12])

class RoundedTextInput(TextInput):
    def __init__(self, **kwargs):
        kwargs.setdefault('foreground_color', (1, 1, 1, 1))
        kwargs.setdefault('padding', [15, 15, 15, 15])
        super().__init__(**kwargs)
        self.background_normal = ''
        self.background_active = ''
        self.background_color = (0, 0, 0, 0)
        self.cursor_color = (0.12, 0.75, 1, 1)
        self.bind(pos=self.update_canvas, size=self.update_canvas)

    def update_canvas(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(0.12, 0.13, 0.18, 1)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[12])
            Color(0.25, 0.26, 0.32, 0.6) 
            Line(rounded_rectangle=(self.x, self.y, self.width, self.height, 12), width=1.2)
# --- АВТОМАТИЧЕСКИЙ ЗАПУСК СИСТЕМНОГО VPN НА ANDROID ---
def android_manage_vpn(action="START"):
    """Автоматически создает VPN-соединение и заворачивает весь трафик телефона"""
    if sys.platform != 'android':
        return False
    try:
        PythonActivity = autoclass('org.kivy.android.PythonActivity')
        Intent = autoclass('android.content.Intent')
        VpnService = autoclass('android.net.VpnService')
        
        current_activity = PythonActivity.mActivity
        
        # Проверяем, давал ли пользователь разрешение на VPN
        prepare_intent = VpnService.prepare(current_activity)
        if prepare_intent is not None:
            # Если не давал — выводим системное окно Android для подтверждения VPN
            current_activity.startActivityForResult(prepare_intent, 0)
            return False

        # Формируем команду для запуска нашей встроенной VPN-службы
        # В buildozer.spec мы добавим этот Java-класс службы
        intent = Intent()
        intent.setClassName(current_activity.getPackageName(), "org.raspidor.bypass.BypassVpnService")
        intent.putExtra("action", action)
        intent.putExtra("split", BYPASS_SETTINGS["split_size"])
        
        if os.path.exists(LIST_FILE):
            intent.putExtra("hostlist", os.path.abspath(LIST_FILE))

        if action == "START":
            current_activity.startService(intent)
        else:
            current_activity.stopService(intent)
        return True
    except Exception as e:
        print(f"Ошибка управления VPN: {str(e)}")
        return False


# --- ГЛАВНЫЙ ЭКРАН RASPIDOR ---
class MainScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        load_domains_from_file()

        root_layout = RelativeLayout()

        self.dots_btn = Button(
            text="•••", font_size='24sp', color=(0.6, 0.6, 0.7, 1),
            background_normal='', background_color=(0, 0, 0, 0),
            size_hint=(None, None), size=('50dp', '50dp'), pos_hint={'top': 0.98, 'right': 0.98}
        )
        self.dots_btn.bind(on_press=self.go_to_settings)

        content_layout = BoxLayout(orientation='vertical', padding=30, spacing=25, size_hint=(1, 0.85), pos_hint={'top': 0.9})

        title_label = Label(text="RASPIDOR", font_size='32sp', bold=True, color=(0.12, 0.75, 1, 1), size_hint_y=0.15)
        self.status_label = Label(text="СТАТУС: ВЫКЛЮЧЕН", font_size='18sp', bold=True, color=(1, 0.3, 0.3, 1), size_hint_y=0.2)
        
        self.btn_start = RoundedButton(text="ЗАПУСТИТЬ RASPIDOR", font_size='20sp', bold=True, size_hint_y=0.3, bg_color=[0.85, 0.24, 0.24, 1])
        self.btn_start.bind(on_press=self.toggle_service)
        
        self.info_label = Label(text="", font_size='13sp', color=(0.4, 0.4, 0.5, 1), halign='center', size_hint_y=0.2)

        content_layout.add_widget(title_label)
        content_layout.add_widget(self.status_label)
        content_layout.add_widget(self.btn_start)
        content_layout.add_widget(self.info_label)
        
        root_layout.add_widget(content_layout)
        root_layout.add_widget(self.dots_btn)
        self.add_widget(root_layout)
        self.update_status_info()

    def update_status_info(self):
        count = len([d for d in BYPASS_SETTINGS["domains"].split("\n") if d.strip()])
        if BYPASS_SETTINGS["mode"] == "auto":
            mode_text = "Автоматический системный VPN" if sys.platform == 'android' else "Локальный ПК режим"
        else:
            mode_text = f"Свой прокси ({BYPASS_SETTINGS['custom_ip']})"
        self.info_label.text = f"Сайтов в списке: {count}\nРежим: {mode_text}"

    def on_enter(self):
        self.update_status_info()

    def go_to_settings(self, instance):
        self.manager.current = 'settings'

    def toggle_service(self, instance):
        global proxy_running, bye_dpi_process
        if not proxy_running:
            anim = Animation(bg_color=[0.18, 0.8, 0.4, 1], duration=0.3)
            anim.start(self.btn_start)
            proxy_running = True

            if BYPASS_SETTINGS["mode"] == "auto":
                if sys.platform == 'android':
                    # Включаем автоматический системный VPN
                    android_manage_vpn("START")
                    self.status_label.text = "СИСТЕМНЫЙ VPN АКТИВЕН"
                else:
                    # Резервный режим запуска бинарника на ПК (если тестируешь)
                    bin_path = "./ciadpi.exe" if sys.platform == "win32" else "./ciadpi"
                    args = [bin_path, "-i", "127.0.0.1", "-p", "1080", "--split", BYPASS_SETTINGS["split_size"]]
                    if os.path.exists(LIST_FILE):
                        args.extend(["--hostlist", LIST_FILE])
                    bye_dpi_process = subprocess.Popen(args)
                    self.status_label.text = "ОБХОД НА ПК ЗАПУЩЕН"
            else:
                self.status_label.text = f"КАСТОМ: {BYPASS_SETTINGS['custom_ip']}:{BYPASS_SETTINGS['custom_port']}"

            self.status_label.color = (0.18, 0.8, 0.4, 1)
            self.btn_start.text = "ОСТАНОВИТЬ"
        else:
            anim = Animation(bg_color=[0.85, 0.24, 0.24, 1], duration=0.3)
            anim.start(self.btn_start)
            proxy_running = False

            if sys.platform == 'android':
                # Выключаем системный VPN
                android_manage_vpn("STOP")
            else:
                if bye_dpi_process:
                    try: bye_dpi_process.terminate()
                    except: pass
                
            self.status_label.text = "СТАТУС: ВЫКЛЮЧЕН"
            self.status_label.color = (1, 0.3, 0.3, 1)
            self.btn_start.text = "ЗАПУСТИТЬ RASPIDOR"
# --- ЭКРАН НАСТРОЕК ---
class SettingsScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = BoxLayout(orientation='vertical', padding=20, spacing=10)

        self.layout.add_widget(Label(text="НАСТРОЙКИ И СПИСОК", font_size='20sp', bold=True, color=(0.12, 0.75, 1, 1), size_hint_y=0.08))
        self.layout.add_widget(Label(text="Выберите режим работы обхода:", font_size='12sp', color=(0.6, 0.6, 0.7, 1), size_hint_y=0.04))
        
        mode_layout = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=0.08)
        self.btn_mode_auto = RoundedButton(text="Автоматический VPN", font_size='11sp')
        self.btn_mode_custom = RoundedButton(text="Свой Прокси", font_size='11sp')
        
        self.btn_mode_auto.bind(on_press=lambda x: self.change_mode("auto"))
        self.btn_mode_custom.bind(on_press=lambda x: self.change_mode("custom"))
        
        mode_layout.add_widget(self.btn_mode_auto)
        mode_layout.add_widget(self.btn_mode_custom)
        self.layout.add_widget(mode_layout)

        self.custom_proxy_layout = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=0.1)
        self.ip_input = RoundedTextInput(text=BYPASS_SETTINGS["custom_ip"], hint_text="IP сервера", font_size='14sp', multiline=False)
        self.port_input = RoundedTextInput(text=BYPASS_SETTINGS["custom_port"], hint_text="Порт", font_size='14sp', multiline=False)
        self.custom_proxy_layout.add_widget(self.ip_input)
        self.custom_proxy_layout.add_widget(self.port_input)
        self.layout.add_widget(self.custom_proxy_layout)

        self.layout.add_widget(Label(text="Список сайтов для фильтра:", font_size='12sp', color=(0.6, 0.6, 0.7, 1), size_hint_y=0.04))
        
        self.domains_input = RoundedTextInput(text=BYPASS_SETTINGS["domains"], multiline=True, font_size='14sp', size_hint_y=0.48)
        self.layout.add_widget(self.domains_input)

        save_btn = RoundedButton(text="СОХРАНИТЬ", font_size='16sp', bold=True, bg_color=[0.12, 0.13, 0.18, 1], size_hint_y=0.1)
        save_btn.bind(on_press=self.save_settings)
        self.layout.add_widget(save_btn)

        self.add_widget(self.layout)
        self.update_mode_ui()

    def change_mode(self, mode):
        BYPASS_SETTINGS["mode"] = mode
        self.update_mode_ui()

    def update_mode_ui(self):
        if BYPASS_SETTINGS["mode"] == "auto":
            self.btn_mode_auto.bg_color = [0.12, 0.75, 1, 0.8]
            self.btn_mode_custom.bg_color = [0.12, 0.13, 0.18, 1]
            self.ip_input.disabled = True
            self.port_input.disabled = True
            self.ip_input.opacity = 0.3
            self.port_input.opacity = 0.3
        else:
            self.btn_mode_auto.bg_color = [0.12, 0.13, 0.18, 1]
            self.btn_mode_custom.bg_color = [0.12, 0.75, 1, 0.8]
            self.ip_input.disabled = False
            self.port_input.disabled = False
            self.ip_input.opacity = 1
            self.port_input.opacity = 1
        self.btn_mode_auto.update_canvas()
        self.btn_mode_custom.update_canvas()

    def save_settings(self, instance):
        BYPASS_SETTINGS["domains"] = self.domains_input.text.strip()
        BYPASS_SETTINGS["custom_ip"] = self.ip_input.text.strip()
        BYPASS_SETTINGS["custom_port"] = self.port_input.text.strip()
        try:
            with open(LIST_FILE, "w", encoding="utf-8") as f:
                f.write(BYPASS_SETTINGS["domains"])
        except: 
            pass
        self.manager.current = 'main'


# --- ТОЧКА ВХОДА ---
class MobileBypassApp(App):
    def build(self):
        self.title = "RASPIDOR"
        sm = ScreenManager()
        sm.add_widget(MainScreen(name='main'))
        sm.add_widget(SettingsScreen(name='settings'))
        return sm
        
    def on_stop(self):
        global proxy_running, bye_dpi_process
        proxy_running = False
        if sys.platform == 'android':
            android_manage_vpn("STOP")
        else:
            if bye_dpi_process:
                try: bye_dpi_process.terminate()
                except: pass

if __name__ == '__main__':
    MobileBypassApp().run()
