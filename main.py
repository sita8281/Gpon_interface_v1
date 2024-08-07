import time
import tkinter as tk
from tkinter import ttk, messagebox
from tkinter import font

import paramiko.ssh_exception

import applib
import sys
import winsound


class InfoWindow(tk.Toplevel):
    def __init__(self, parent, title, width, height, bg=None):
        super().__init__(parent, bg=bg)
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        win_width, win_height = width, height
        x_coordinate = int((screen_width / 2) - (win_width / 2))
        y_coordinate = int((screen_height / 2) - (win_height / 2))
        self.geometry(f"{win_width}x{win_height}+{x_coordinate}+{y_coordinate}")
        self.title(title)  # подпись окна
        self.iconphoto(False, tk.PhotoImage(file='images/ssh_icon.png'))


class BlockWindow(tk.Toplevel):
    def __init__(self, parent, width, height, bg='grey20'):
        super().__init__(parent, bg=bg)
        self.resizable(False, False)
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        win_width, win_height = width, height
        x_coordinate = int((screen_width / 2) - (win_width / 2))
        y_coordinate = int((screen_height / 2) - (win_height / 2))
        # self.overrideredirect(True)
        self.geometry(f"{win_width}x{win_height}+{x_coordinate}+{y_coordinate}")
        label = tk.Label(self, text='Ожидание ответа от GPON блока...', font=('Arial', 20, 'bold'),
                         foreground='#61FFD6', background='grey20')
        label.place(x=20, y=125)

        self.canvas = tk.Canvas(self, height=450, width=800)
        self.img = tk.PhotoImage(file='images/wait_gpon.png')
        self.canvas.create_image(0, 0, anchor='nw', image=self.img)
        self.canvas.place(x=0, y=0)
        self.canvas.create_text(400, 220, fill='black', font=('Arial', 20, 'bold'), text='Ожидание ответа от GPON блока...')
        self.c_text = self.canvas.create_text(170, 250, fill='black', font=('Arial', 14, 'bold'), text='', anchor='nw')

    def insert_text(self, text: str):
        self.canvas.delete(self.c_text)
        self.c_text = self.canvas.create_text(170, 250, fill='black', font=('Arial', 14, 'bold'), text=text, anchor='nw')


class SearchSnWin(InfoWindow):
    def __init__(self, parent):
        super().__init__(parent, 'Поиск ONU по серийному номеру', 400, 150)

        self.resizable(False, False)
        self.grab_set()
        self.focus()

        self.parent = parent
        self.ssh = parent.ssh
        self.count = 0
        self.count_clr = 0
        self.result = ''
        self.id_onu = []
        self.sn_onu = []
        self.port_ = None
        self.onu_ = None
        self.gen = None
        self.label_succes = None
        self.sn_ = ''

        # определение к какому блоку gpon подкл. программа
        if self.parent.name_block_olt == 'garage':
            self.ports = 8
        else:
            self.ports = 16

        # меню виджет
        self.menu = tk.Menu(self, tearoff=0)
        self.menu.add_command(command=self.copy_sn, label='Копировать')
        self.menu.add_command(command=lambda : self.paste_sn(0), label='Вставить')

        # фрейм №1 (картинка, поле ввода, кнопка)
        # ============================================
        self.frame1 = tk.Frame(self)
        self.frame1.place(x=0, y=0, width=400, height=150)

        self.img = tk.PhotoImage(file='images/icon_search_sn.png')
        self.canvas = tk.Canvas(self.frame1)
        self.canvas.place(x=20, y=10, width=130, height=130)
        self.canvas.create_image(0, 0, image=self.img, anchor='nw')

        self.label = tk.Label(self.frame1, font='arial 12', text='введите серийный номер:')
        self.label.place(x=170, y=15)
        self.valid_info = tk.StringVar()
        self.label_valid_info = tk.Label(self.frame1, font='arial 10 bold', textvariable=self.valid_info, fg='red')
        self.label_valid_info.place(x=170, y=70)

        self.entry = ttk.Entry(self.frame1, font='arial 13 bold')
        self.entry.place(x=170, y=40, width=200, height=30)
        self.entry.bind('<Button-3>', self.open_menu)

        self.button = ttk.Button(self.frame1, text='Начать поиск', command=self.start_search)
        self.button.place(x=250, y=110, width=120)

        # фрейм №2 (колесо загрузки, текст о ходе процесса)
        # ================================================
        self.frame2 = tk.Frame(self)
        self.frame2.place(x=0, y=0, width=400, height=150)

        self.img_animation = [tk.PhotoImage(file='images/loading.gif', format=f'gif -index {i}') for i in range(16)]
        self.canvas_anim = tk.Canvas(self.frame2)
        self.canvas_anim.place(x=10, y=10, width=120, height=120)
        self.animation_load() # запуск анимации прогрузки

        self.text = tk.Text(self.frame2, bg='grey94', bd=1, font='arial 9')
        self.text.place(x=150, y=5, width=228, height=140)
        self.scrolltxt = ttk.Scrollbar(self.frame2, orient='vertical', command=self.text.yview)
        self.scrolltxt.place(x=380, y=5, height=140)
        self.text.config(yscrollcommand=self.scrolltxt.set)

        # фрейм №3 (не удалось найти ONU с указанным SN)
        # ================================================
        self.frame3 = tk.Frame(self)
        self.frame3.place(x=0, y=0, width=400, height=150)

        self.img_warning = tk.PhotoImage(file='images/warning.png')
        self.canvas_warning = tk.Canvas(self.frame3)
        self.canvas_warning.place(x=20, y=20, width=120, height=120)
        self.canvas_warning.create_image(5, 5, image=self.img_warning, anchor='nw')
        self.label_warning = tk.Label(self.frame3, text='Не удалось найти ONU', font='arial 10')
        self.label_warning.place(x=180, y=60)
        self.button_destroy = ttk.Button(self.frame3, text='Завершить', command=self.destroy)
        self.button_destroy.place(x=220, y=110)

        # фрейм №4 (ONU найдена)
        # ================================================
        self.frame4 = tk.Frame(self)
        self.frame4.place(x=0, y=0, width=400, height=150)

        self.img_succes = tk.PhotoImage(file='images/succes.png')
        self.canvas_succes = tk.Canvas(self.frame4)
        self.canvas_succes.place(x=20, y=5, width=120, height=120)
        self.canvas_succes.create_image(5, 5, image=self.img_succes, anchor='nw')
        self.var_success = tk.StringVar()
        self.var_success.set('ONU найдена')
        self.label_succes = tk.Label(self.frame4, textvariable=self.var_success, font='arial 10')
        self.label_succes.place(x=180, y=60)
        self.button_show = ttk.Button(self.frame4, text='Показать', command=self.open_onu)
        self.button_show.place(x=190, y=110)

        self.frame1.tkraise()

    def animation_load(self):
        self.count += 1
        if self.count == 16:
            self.count = 0
            for i in self.canvas_anim.find_all():
                self.canvas_anim.delete(i)
        self.canvas_anim.create_image(0, 0, anchor='nw', image=self.img_animation[self.count])

        self.after(50, self.animation_load)

    def open_menu(self, event):
        self.menu.post(event.x_root, event.y_root)

    def copy_sn(self):
        self.clipboard_clear()
        self.clipboard_append(self.entry.get())

    def paste_sn(self, event):
        self.entry.delete(0, tk.END)
        self.entry.insert(0, self.clipboard_get())

    def start_search(self):
        self.sn_ = self.entry.get()
        if applib.sn_validation(self.sn_):
            self.frame2.tkraise()
            self.protocol('WM_DELETE_WINDOW', self.pass_f)
            self.start_sn_parsing()

        else:
            self.valid_info.set('Неверный формат S/N')
            winsound.PlaySound('SystemHand', winsound.SND_ASYNC)

    def pass_f(self):
        # просто заглушка
        pass

    def create_generator(self):
        for i in range(self.ports):
            self.port_ = i
            self.process_sn_parsing(number_port=i)

            yield i

    def start_sn_parsing(self):
        self.gen = self.create_generator()
        next(self.gen)

    def process_sn_parsing(self, number_port):
        self.ssh.send_data(f'display ont info {number_port} all\n')
        self.ssh.send_data('          \n\n\n')

        self.text.insert(tk.END, f'\nПорт №{self.port_}...')
        self.text.see(tk.END)

        self.after(500, self.recv_sn_parsing)

    def recv_sn_parsing(self):
        out = self.ssh.receive_data()
        if out is not False:
            self.result += out
            self.after(300, self.recv_sn_parsing)  # задержка 0.3 секунды, для корректности работы ssh

            # как только gpon блок завершил передавать данные
            # начинается формирование первичного вложенного списка
        else:

            # поиск id,name,sn,status в буфере 'result'
            self.id_onu = applib.parsed_id(self.result)
            self.sn_onu = applib.parsed_sn(self.result)

            if self.id_onu is False or self.sn_onu is False:
                self.id_onu = []
                self.sn_onu = []

            if len(self.id_onu) != len(self.sn_onu):
                self.destroy()
                tk.messagebox.showerror('Ошибка', 'Ошибка данных, возможно пришли битые пакеты\nпопробуйте ещё раз.')
                return 0

            for count, i in enumerate(self.id_onu):
                if self.sn_onu[count] == self.sn_:

                    self.frame4.tkraise()
                    self.protocol('WM_DELETE_WINDOW', self.destroy)
                    winsound.PlaySound('SystemAsterisk', winsound.SND_ASYNC)
                    self.onu_ = i
                    return 0

            self.result = ''

            self.text.insert(tk.END, 'серийник не найден.')
            self.text.see(tk.END)
            try:
                next(self.gen)
            except StopIteration:
                self.frame3.tkraise()
                self.protocol('WM_DELETE_WINDOW', self.destroy)
                winsound.PlaySound('SystemExclamation', winsound.SND_ASYNC)

    def open_onu(self):

        self.var_success.set('Выполняется открытие...')
        self.button_show['state'] = tk.DISABLED
        self.after(1, lambda : self.parent.open_select_onu(self.port_, self.onu_, self.destroy))


class TimerWindow(InfoWindow):
    def __init__(self, parent):
        super().__init__(parent, 'Программа работает больше 10 минут', 550, 200)
        self.lift()
        parent.update()
        self.focus()
        parent.update()
        self.t_var = tk.StringVar()
        self.count = 30
        self.flag = True

        self.protocol('WM_DELETE_WINDOW', lambda : 1)

        self.img = tk.PhotoImage(file='images/timer_wr.png')
        self.canvas = tk.Canvas(self, width=160, height=160)
        self.canvas.create_image(0, 0, anchor='nw', image=self.img)
        self.canvas.place(x=30, y=20)

        self.label = tk.Label(self, textvariable=self.t_var, font='Arial 16 bold', fg='red')
        self.label.place(x=250, y=20)
        self.label_inf = tk.Label(self, text='Продолжить работу программы?', font='Arial 10')
        self.label_inf.place(x=280, y=120)

        self.btn = ttk.Button(self, text='Да', command=self.destroy)
        self.btn1 = ttk.Button(self, text='Нет', command=self.close)
        self.btn.place(x=300, y=150)
        self.btn1.place(x=400, y=150)

        self.loop_t()

    def loop_t(self):
        if self.count == 0:
            sys.exit()
        self.t_var.set(f'До закрытия программы\n осталось {self.count} секунд')
        self.count -= 1
        self.after(1000, self.loop_t)

    def close(self):
        self.destroy()
        sys.exit()


class GarageLabelFrame(ttk.LabelFrame):
    def __init__(self, parent):
        super().__init__(parent)
        self.config(text='Гараж')
        self.button = ttk.Button(self, text='Выбрать')
        self.button.grid(column=1, row=3, sticky='e', pady=5, padx=10)
        self.label1 = ttk.Label(self, text='Логин:').grid(column=0, row=0, pady=5, padx=10)
        self.label2 = ttk.Label(self, text='Пароль:').grid(column=0, row=1, pady=5, padx=10)
        self.label3 = ttk.Label(self, text='Сервер:').grid(column=0, row=2, pady=5, padx=10)
        self.entry1 = ttk.Entry(self, width=25)
        self.entry2 = ttk.Entry(self, width=25)
        self.entry3 = ttk.Entry(self, width=25)
        self.entry1.grid(column=1, row=0, pady=5, padx=10)
        self.entry2.grid(column=1, row=1, pady=5, padx=10)
        self.entry3.grid(column=1, row=2, pady=5, padx=10)


# класс фрейма пятиэтажки
# наследуется от класса фрейма гаража (GarageLabelFrame)
class FiveStageLabelFrame(GarageLabelFrame):
    def __init__(self, parent):
        super().__init__(parent)
        self.config(text='Пятиэтажка')


class StartWin(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title('Выбор GPON блока')
        self.resizable(False, False)

        # кусок кода для центровки окна в середину экрана
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        win_width, win_height = 620, 340
        x_coordinate = int((screen_width / 2) - (win_width / 2))
        y_coordinate = int((screen_height / 2) - (win_height / 2))
        self.geometry(f"{win_width}x{win_height}+{x_coordinate}+{y_coordinate}")
        self.iconphoto(False, tk.PhotoImage(file='images/ssh_icon.png'))
        self.lift()

        # размещение изображения в верхней части окна
        self.canvas = tk.Canvas(self, height=150, width=900)
        self.img = tk.PhotoImage(file='images/sys_image.png')
        self.image = self.canvas.create_image(0, 0, anchor='nw', image=self.img)
        self.canvas.place(x=0, y=0)
        # помещаем в окне 2 фрейма:
        # 1 - для гаража
        # 2 - для пятиэтажки
        self.garage = GarageLabelFrame(self)
        self.garage.place(x=10, y=170)
        self.etag5 = FiveStageLabelFrame(self)
        self.etag5.place(x=320, y=170)
        # берёт из файла connectdata.data сохраненные ранее данные login, passw, ip
        self.insert_user_passw_ip()

        self.garage.button['command'] = self._save_garage  # при нажатии кнопки гаража, вызывает save_garage
        self.etag5.button['command'] = self._save_etag5  # при нажатии кнопки гаража, вызывает save_etag5

    # 2 метода вызывают метод save_user_passw_ip и передают инфу какой gpon блок был выбран
    def _save_garage(self):
        app.selected_gpon = 'garage'
        self.save_user_passw_ip('garage')

    def _save_etag5(self):
        app.selected_gpon = 'etag5'
        self.save_user_passw_ip('etag5')

    # метод валидации и сохранения
    # если валидация пройдена, то данные сохранятся, иначе появляется msg_box
    # далее вызывается метод start из класса MainWin (объект app)
    # и окно app1 (класс StartupWin) уничтожается
    def save_user_passw_ip(self, target):
        # помещаем данные из полей ввода в var1 (гараж) и var2 (пятиэтажка)
        var1 = [self.garage.entry1.get(), self.garage.entry2.get(), self.garage.entry3.get()]
        var2 = [self.etag5.entry1.get(), self.etag5.entry2.get(), self.etag5.entry3.get()]
        # валидируем поля логина и пароля (validate_var1, validate_var2 = bool)
        validate_var1 = applib.user_passw_validation(var1[0], var1[1])
        validate_var2 = applib.user_passw_validation(var2[0], var2[1])
        # валидируем поля IP адресов (validate_ip_var1, validate_ip_var2 = bool)
        validate_ip_var1 = applib.ip_validation(var1[2])
        validate_ip_var2 = applib.ip_validation(var2[2])
        # проверка пройдена ли валдации или нет
        if validate_var1 and validate_var2:
            if validate_ip_var1 and validate_ip_var2:
                applib.save_data(var1, var2)
                if target == 'garage':
                    app.name_block_olt = target
                    app.target_connection = var1
                elif target == 'etag5':
                    app.name_block_olt = target
                    app.target_connection = var2
                self.destroy()  # уничтожить окно
                app.start()  # устанавлиет сессию с блоком и откр. осн. окно
            else:
                msg = ['1) Поле не дожно быть пустым\n',
                       '2) Допустимые символы: [0-9]\n',
                       '3) Формат IP: XXX.XXX.XXX.XXX\n']
                messagebox.showwarning('Ошибка: некорректный IP адрес', ''.join(msg))

        else:
            msg = ['1) Допустимые символы: [A-Z, a-z, _, 0-9]\n',
                   '2) Допустимая длинна имени пользователя: [4-16 символов]\n',
                   '3) Допустимая длинна пароля: [5-16 символов]\n',
                   '4) Поле ввода не должно быть пустым']
            messagebox.showwarning('Ошибка: недопустимые символы', ''.join(msg))

        # метод загрузки ip, login, passw из файла
        # и вставка данных в поля
    def insert_user_passw_ip(self):
        var1, var2 = applib.load_data()
        self.garage.entry1.insert(0, var1[0])
        self.garage.entry2.insert(0, var1[1])
        self.garage.entry3.insert(0, var1[2])
        self.etag5.entry1.insert(0, var2[0])
        self.etag5.entry2.insert(0, var2[1])
        self.etag5.entry3.insert(0, var2[2])


class MainWin(tk.Tk):
    def __init__(self):
        super().__init__()
        self.last_elem = ''
        self.table_list = []
        self.BLOCK_FLAG = False
        self.ssh = None
        self.target_connection = None
        self.name_block_olt = None
        self.result = ''
        self.result_optical = ''
        self.result_dist = ''
        self.id_onu = None
        self.name_onu = None
        self.sn_onu = None
        self.status_onu = None
        self.number_port = None
        self.LIST = []
        self.selected_gpon = None
        self.flag = True
        self.count = 0
        self.monitoring_table = None
        self.item = None
        self.toplevel_win = None
        self.labels1 = None
        self.delete_onu_win = None
        self.entry_reg = None
        self.searched_port = None
        self.vlan4 = 4
        self.vlan5 = 5
        self.reg_id_ont = None
        self.input_name_win = None
        self.auto_reg_win = None
        self.labels2 = None
        self.GLOBAL_TIMER = 600000
        self.txt_progress = tk.StringVar()
        self.progress_counter = 0
        self.vlan_id = ''

        self.style = ttk.Style()
        self.style.map("Treeview",
                       foreground=self.fixed_map('foreground'),
                       background=self.fixed_map('background')
                       )

        # кусок кода отвечающий за центровку открывшегося окна в центр монитора
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        print(screen_width, screen_height)
        win_width, win_height = 1300, 800
        x_coordinate = int((screen_width / 2) - (win_width / 2))
        y_coordinate = int((screen_height / 2) - (win_height / 2))
        self.geometry(f"{win_width}x{win_height}+{x_coordinate}+{y_coordinate}")

        self.withdraw() # прячем основное окно
        # при закрытии основного окна, вызваем метод: closed
        # открываем окно ввода и валидации логина, пароля, ip
        self.iconphoto(False, tk.PhotoImage(file='images/ssh_icon.png'))
        self.start_window = StartWin(self)

        self.start_window.protocol("WM_DELETE_WINDOW", self.destroy) # если окно закрывют, тогда завершаем программу

        # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++#
        #  создаём фрейм в котором находятся кнопки меню с иконками, их 5 штук       #
        # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++#

        self.menu_widgets = tk.Frame(self)
        self.menu_widgets.place(x=5, y=5)
        # подгружаем иконки кнопок, пишем их в список
        self.images = [tk.PhotoImage(file=f'images/icon{i}.png') for i in range(5)]
        # текста кнопок, 1 элемент для 1 кнопки
        self.text_buttons = ['Расширенный\nрежим',
                             'Отобразить\nтаблицу',
                             'Ручная\nрегистрация ONU',
                             'Автоматическая\nрегистрация ONU',
                             'Найти ONU по\nсерийнику']
        # создаем кнопки и помещаем их в список
        self.buttons = [tk.Button(self.menu_widgets,
                                  text=self.text_buttons[i],
                                  compound='top',
                                  font='arial 10',
                                  relief='flat',
                                  image=self.images[i]) for i in range(5)]

        self.buttons[0]['command'] = lambda : self.raise_frame(self.main_frame)
        self.buttons[1]['command'] = lambda : self.raise_frame(self.main_frame_1)
        self.buttons[4]['command'] = self.search_sn_win
        self.buttons[2]['command'] = lambda : tk.messagebox.showwarning('В разрботке', 'Артём работает над этой функцией\nавтоматический режим уже сделал')
        self.buttons[3]['command'] = self.reg_onu_auto
        # размещаем кнопки во фрейме
        for i in range(5):
            self.buttons[i].grid(column=0, row=i, padx=5, pady=5, sticky='nsew')

        # бинды событий кнопок
        # при наведении курсора на кнопку текст подчёркивается и меняет цвет
        # само тело кнопки при наведении тоже меняет цвет
        self.buttons[0].bind('<Enter>', lambda x: set_color_focus(self.buttons[0]))
        self.buttons[0].bind('<Leave>', lambda x: del_color_focus(self.buttons[0]))
        self.buttons[1].bind('<Enter>', lambda x: set_color_focus(self.buttons[1]))
        self.buttons[1].bind('<Leave>', lambda x: del_color_focus(self.buttons[1]))
        self.buttons[2].bind('<Enter>', lambda x: set_color_focus(self.buttons[2]))
        self.buttons[2].bind('<Leave>', lambda x: del_color_focus(self.buttons[2]))
        self.buttons[3].bind('<Enter>', lambda x: set_color_focus(self.buttons[3]))
        self.buttons[3].bind('<Leave>', lambda x: del_color_focus(self.buttons[3]))
        self.buttons[4].bind('<Enter>', lambda x: set_color_focus(self.buttons[4]))
        self.buttons[4].bind('<Leave>', lambda x: del_color_focus(self.buttons[4]))

        def set_color_focus(btn, event=None):
            # btn['bg'] = '#E0FFFF'
            # btn['fg'] = 'white'
            btn['font'] = 'arial 10 underline'
            btn['relief'] = 'raised'

        def del_color_focus(btn, event=None):
            # btn['bg'] = 'grey94'
            # btn['fg'] = 'black'
            btn['font'] = 'arial 10'
            btn['relief'] = 'flat'

        # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++#
        #  фрейм с другими фреймами которые относятся к расширенному режиму           #
        # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++#
        self.main_frame = tk.Frame(self)
        self.main_frame.place(x=130, y=5, width=1100, height=730)

        # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++#
        #  фрейм с древовидной таблицей                                               #
        # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++#
        self.tree_frame = tk.Frame(self.main_frame, relief='sunken', width=400, height=690, bd=2)
        self.tree_frame.place(x=5, y=5)
        self.tree = ttk.Treeview(self.tree_frame, height=33, selectmode='browse')
        self.tree.heading('#0', text='Huawei MA5608T (список портов)')
        self.tree.column('#0', width=370)
        self.tree.place(x=0, y=0)

        self.y_scroll = ttk.Scrollbar(self.tree_frame, orient='vertical', command=self.tree.yview)
        self.y_scroll.place(x=375, y=1, height=685)
        self.tree.configure(yscroll=self.y_scroll.set)

        self.img = tk.PhotoImage(file='images/folder_icon.png')
        self.img_1 = tk.PhotoImage(file='images/onu_icon.png')

        self.tree.bind('<<TreeviewOpen>>', self.insert_list_onu)
        self.tree.bind('<<TreeviewSelect>>', self.select_onu)
        self.tree.bind("<Motion>", self.motion_treeview)
        self.tree.bind("<Leave>", self.leave_treeview)
        self.tree.tag_configure('default', foreground='black', font='Helvetica 9')
        self.tree.tag_configure('shot', foreground='blue', font='Helvetica 9 underline')



        for i in range(16):
            self.tree.insert('', iid=f'port {i}', index=tk.END, text=f' Порт_{i}', image=self.img, open=False, tags=('default',))
            self.tree.insert(f'port {i}', tk.END, text='')

        # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++#
        #  фрейм с выводом оптической информации, и другой инфы                       #
        # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++#

        self.optical_info_frame = tk.Frame(self.main_frame, width=480, height=400, relief='raised', bd=2)
        self.optical_info_frame.place(x=425, y=10)

        self.labels = [tk.Label(self.optical_info_frame, width=25, anchor='w') for _ in range(7)]
        self.labels_info = [tk.Label(self.optical_info_frame, width=40, fg='blue', anchor='w', relief='groove') for _ in range(7)]
        self.labels_text_lst = ['Название вендора',
                                'Rx optical power(dBm)',
                                'Tx optical power(dBm)',
                                'Обратный Rx optical(dBm)',
                                'Сила тока в лазере(mA)',
                                'Температура(C)',
                                'Напряжение(V)']
        y_count = 20
        for i in range(7):
            self.labels[i].place(x=5, y=y_count)
            self.labels_info[i].place(x=160, y=y_count)
            self.labels[i]['text'] = f'{self.labels_text_lst[i]} :'
            y_count += 19

        self.label_check_box = tk.Label(self.optical_info_frame, width=10, font='tkDefaultFont 10 bold', anchor='w', text='Вывести')
        self.label_check_box.place(x=5, y=160)

        self.FLAG_DISPLAY_OPTICAL = tk.BooleanVar()
        self.FLAG_DISPLAY_OPTICAL.set(True)

        self.check_btn = tk.Checkbutton(self.optical_info_frame, variable=self.FLAG_DISPLAY_OPTICAL)
        self.check_btn.place(x=70, y=160)

        self.labels_default = [tk.Label(self.optical_info_frame, width=25, anchor='w') for _ in range(7)]
        self.labels_info_default = [tk.Label(self.optical_info_frame, width=40, anchor='w', relief='groove', fg='#00008B') for _ in range(7)]

        self.labels_text_lst_default = ['Серийный номер',
                                        'Последнее включение',
                                        'Последнее выключение',
                                        'Растояние до ONU (м)',
                                        'Загрузка RAM',
                                        'Загрузка CPU',
                                        'Длительность онлайна']
        y_count = 190
        for i in range(7):
            self.labels_default[i].place(x=5, y=y_count)
            self.labels_info_default[i].place(x=160, y=y_count)
            self.labels_default[i]['text'] = f'{self.labels_text_lst_default[i]} :'
            y_count += 19

        self.label_check_box = tk.Label(self.optical_info_frame, width=10, font='tkDefaultFont 10 bold', anchor='w', text='Вывести')
        self.label_check_box.place(x=5, y=330)

        self.FLAG_DISPLAY_DEFAULT = tk.BooleanVar()
        self.FLAG_DISPLAY_DEFAULT.set(False)

        self.check_btn = tk.Checkbutton(self.optical_info_frame, variable=self.FLAG_DISPLAY_DEFAULT)
        self.check_btn.place(x=70, y=330)

        self.delete_img = tk.PhotoImage(file='images/delete_icon.png')
        self.mac_img = tk.PhotoImage(file='images/mac_icon.png')
        self.monitoring_img = tk.PhotoImage(file='images/icon_monitoring.png')
        self.mac_button = tk.Button(self.main_frame, image=self.mac_img, text='Найти MAC\nвыбранной ONU', compound='top', command = lambda :tk.messagebox.showwarning('В разрботке', 'Артём работает над этой функцией'))
        self.delete_button = tk.Button(self.main_frame, image=self.delete_img, text='Удалить\nвыбранную ONU', compound='top', command = self.create_delete_onu_win)
        self.monitoring_button = tk.Button(self.main_frame, image=self.monitoring_img, text='Авто обновление\nсигнала', compound='top', command = self.open_monitoring_window)
        self.delete_button.place(x=430, y=430, height=140, width=100)
        self.mac_button.place(x=550, y=430, height=140, width=100)
        self.monitoring_button.place(x=670, y=430, height=140, width=100)

        # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
        # фрейм в котором распологается фрейм таблицы, радиокнопки и т.д
        # +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

        self.main_frame_1 = tk.Frame(self)
        self.main_frame_1.place(x=130, y=5, width=1100, height=730)

        # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++#
        #  фрейм с таблицей                                                           #
        # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++#

        self.table_frame = tk.Frame(self.main_frame_1, width=750, height=690, relief='sunken',bd=2)
        self.table_frame.place(x=5, y=5)

        columns = ('id', 'name', 'sn', 'status', 'signal', 'distance')
        self.table = ttk.Treeview(self.table_frame, show='headings', columns=columns, height=33, selectmode='browse')
        self.table.column('id', width=50, anchor='w')
        self.table.column('name', width=250, anchor='w')
        self.table.column('sn', width=150, anchor='w')
        self.table.column('status', width=70, anchor='w')
        self.table.column('signal', width=100, anchor='w')
        self.table.column('distance', width=100, anchor='w')
        self.table.heading('id', text='ID')
        self.table.heading('name', text='NAME')
        self.table.heading('sn', text='SN')
        self.table.heading('status', text='STATUS')
        self.table.heading('signal', text='RX OPTICAL')
        self.table.heading('distance', text='DISTANCE')
        self.table.place(x=0, y=0)

        self.table_scroll_bar = ttk.Scrollbar(self.table_frame, orient='vertical', command=self.table.yview)
        self.table.configure(yscroll=self.table_scroll_bar.set)
        self.table_scroll_bar.place(x=725, y=1, height=684)

        # меню таблицы                                                               #
        # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++#

        def open_menu(event):
            self.table.identify_row(event.y)
            print(event)
            self.table_menu.post(event.x_root, event.y_root)

        def copy_id():
            i = self.table.selection()
            self.clipboard_clear()
            if self.table.item(i, option='value'):
                iid= self.table.item(i, option='value')[0]
                self.clipboard_append(iid)

        def copy_addr():
            i = self.table.selection()
            self.clipboard_clear()
            if self.table.item(i, option='value'):
                name = self.table.item(i, option='value')[1]
                self.clipboard_append(name)

        def copy_sn(event):
            i = self.table.selection()
            self.clipboard_clear()
            if self.table.item(i, option='value'):
                sn = self.table.item(i, option='value')[2]
                self.clipboard_append(sn)

        self.table_menu = tk.Menu(self.table, tearoff=0)
        self.table_menu.add_command(command=lambda : copy_sn(0), label='Копировать SN')
        self.table_menu.add_command(command=copy_id, label='Копировать номер ONT')
        self.table_menu.add_command(command=copy_addr, label='Копировать адрес ONT')

        self.table.bind('<Double-Button-1>', open_menu)
        self.table.bind('<Control-Key-c>', copy_sn) #копировать серийник при нажатии ctrl+C

        # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++#
        #  фрейм с радиокнопками, чекбоксами и кнопками                               #
        # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++#

        self.radio_button_frame = tk.Frame(self.main_frame_1, width=230,height=720, relief='raised', bd=2)
        self.radio_button_frame.place(x=780, y=10)

        self.radio_button_var = tk.IntVar()
        self.radio_button_var.set(0)
        self.radio_buttons = [tk.Radiobutton(self.radio_button_frame, text=f'Выбрать: порт {i}', value=i, variable=self.radio_button_var) for i in range(16)]
        y_count = 40
        for i in range(16):
            self.radio_buttons[i].place(x=10, y=y_count)
            y_count += 25
        self.label_radio_btns = tk.Label(self.radio_button_frame, text='Список портов:', font='tkDefaultFont 10 bold')
        self.label_radio_btns.place(x=10, y=10)
        self.label_radio_btns = tk.Label(self.radio_button_frame, text='Выводить список:', font='tkDefaultFont 10 bold')
        self.label_radio_btns.place(x=10, y=450)

        self.check_btn_var = tk.BooleanVar()
        self.check_btn_var1 = tk.BooleanVar()
        self.check_btn_var.set(0)
        self.check_btn_var1.set(0)
        self.check_buttons_text = ['Сигналов (замедляет алгоритм)', 'Дистанций (замедляет алгоритм)']
        self.check_buttons = [tk.Checkbutton(self.radio_button_frame, text=f'{i}') for i in self.check_buttons_text]
        self.check_buttons[0].config(variable=self.check_btn_var, onvalue=1, offvalue=0)
        self.check_buttons[1].config(variable=self.check_btn_var1, onvalue=1, offvalue=0)
        y_count = 470
        for i in range(2):
            self.check_buttons[i].place(x=10, y=y_count)
            y_count += 25

        self.label_radio_btns = tk.Label(self.radio_button_frame, text='Сортировать по:', font='tkDefaultFont 10 bold')
        self.label_radio_btns.place(x=10, y=525)
        self.text_sort_buttons = ['Сигналам', 'Дистанциям', 'Именам', 'Номерам']
        self.sort_buttons = [tk.Button(self.radio_button_frame, text=f'{i}', width=10) for i in self.text_sort_buttons]

        self.sort_buttons[0]['command'] = lambda :self.sort_table(applib.sort_signals)
        self.sort_buttons[1]['command'] = lambda :self.sort_table(applib.sort_distance)
        self.sort_buttons[2]['command'] = lambda :self.sort_table(applib.sort_name)
        self.sort_buttons[3]['command'] = lambda :self.sort_table(applib.sort_id)
        y_count = 550
        for i in range(4):
            self.sort_buttons[i].place(x=10, y=y_count)
            y_count += 26

        self.start_img = tk.PhotoImage(file='images/start_icon.png')
        self.start_button = tk.Button(self.radio_button_frame, image=self.start_img, command=self.press_start_btn)
        self.start_button.place(x=130, y=570)

        self.frame_progress = tk.Frame(self.main_frame_1)
        self.frame_progress.place(x=790, y=675, width=200, height=45)

        # прогресс-бар
        self.progress = ttk.Progressbar(self.frame_progress, mode='determinate')
        self.progress.place(x=0, y=0, width=200, height=25)

        # вывод инфы под прогресс-баром
        self.progress_label = tk.Label(self.frame_progress, textvariable=self.txt_progress, font='arial 9', fg='blue')
        self.progress_label.place(x=0, y=25)
        self.txt_progress.set('')

        # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++#
        #  фрейм автомониторинга сигнала, в нем распологаются другие феймы            #
        # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++#

        self.main_frame_4 = tk.Frame(self)
        self.main_frame_4.place(x=130, y=5, width=1100, height=700)

        # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++#
        #  фрейм автомониторинга сигнала, в нем распологаются другие феймы            #
        # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++#

        self.spinbox_ports = tk.Listbox(self.main_frame_4, )
        self.spinbox_ports.place(x=10, y=10)

        self.raise_frame(self.main_frame)  # открываем сразу первый фрейм с treeview

    def motion_treeview(self, e):
        # print(self.tree.identify_row(e.y))
        elem = self.tree.identify_row(e.y)
        if elem != self.last_elem:
            if elem == '':
                self.tree.item(self.last_elem, tags=('default',))
                self.last_elem = ''
            else:
                self.tree.item(self.last_elem, tags=('default',))
                self.tree.item(elem, tags=('shot',))
                self.last_elem = elem

    def leave_treeview(self, e):
        self.tree.item(self.last_elem, tags=('default',))

    def reg_onu_auto(self):
        self.result = ''
        if self.selected_gpon == 'garage':
            count_ports = 8
        else:
            count_ports = 16

        self.auto_reg_win = InfoWindow(self, bg='grey20', height=400, width=600, title='Регистрация ONU')
        self.auto_reg_win.grab_set()
        self.auto_reg_win.protocol('WM_DELETE_WINDOW',
                                   lambda: tk.messagebox.showerror('Так делать не надо', 'Программа выполняет алгоритм, не хорошо её закрывать', parent=self.auto_reg_win))

        self.labels2 = [tk.Label(self.auto_reg_win, fg='#00FF7F', font='arial 13 bold', bg='grey20') for _ in range(16)]

        y = 0
        for i in self.labels2:
            i.place(x=10, y=y)
            y += 20

        self.labels2[0]['text'] = 'Регистрация ONU...'

        for port in range(count_ports):
            self.ssh.send_data(f'display ont autofind {port}\n')
            self.ssh.send_data(f'\n\n\n')

        self.labels2[1]['text'] = 'Запросы на все порты отправлены. '
        self.after(1500, self.reg_onu_recv)

    def reg_onu_recv(self):
        self.labels2[2]['text'] = 'Сканирование портов на наличие незарегистрированных ONU...'
        out = self.ssh.receive_data()
        if out is not False:
            self.result += out
            self.after(1500, self.reg_onu_recv)
        else:
            self.labels2[3]['text'] = 'Сканирование завершено.'

            lines = self.result.splitlines()
            answer = 2
            for line in lines:
                self.searched_port = applib.check_autofind_ont(line)
                if self.searched_port is not False:
                    if self.searched_port != 'onu not found':
                        print(self.searched_port)
                        answer = tk.messagebox.askyesno('Найдена ONU', f'Найдена незарегистрованная ONU\n\nНомер порта: [{self.searched_port}]\n\nДа - начать регистрацию ONU\n\nНет - продолжить поиск новых ONU', parent=self.auto_reg_win)
                        if answer:
                            self.reg_onu_name()
                            break
                        else:
                            pass
            if not answer:
                self.auto_reg_win.destroy()
                tk.messagebox.showinfo('Информация', 'На GPON блоке больше нет незарегистрированных ONU')
            if answer == 2:
                self.auto_reg_win.destroy()
                tk.messagebox.showwarning('Не удалось найти ONU', 'Незарегистрированные ONU не найдены на GPON блоке')

    def reg_onu_name(self):
        self.input_name_win = InfoWindow(self.auto_reg_win, height=200, width=400, title='Регистрация')
        self.input_name_win.protocol('WM_DELETE_WINDOW', self.auto_reg_win.destroy)  # есди нажали крестик, то закроется и окно регистрации
        self.input_name_win.grab_set()
        label = tk.Label(self.input_name_win, text='Введите имя ONU:', font='arial 10 bold')
        label1 = tk.Label(self.input_name_win, text='Допустимые цифры и буквы: 0-9, A-Z, a-z', font='arial 10')
        label2 = tk.Label(self.input_name_win, text='Допустимые символы: _ / ( ) -', font='arial 10')
        label3 = tk.Label(self.input_name_win, text='Выберите VLAN:', font='arial 10 bold')
        label1.place(x=10, y=80)
        label2.place(x=10, y=100)
        label3.place(x=10, y=50)
        label.place(x=10, y=20)
        self.entry_reg = ttk.Entry(self.input_name_win, width=35, font='arial 10 bold')
        self.entry_reg.place(x=140, y=20)

        if self.selected_gpon == 'garage':
            self.combobox = ttk.Combobox(self.input_name_win, state='readonly', values=['5'])
            self.combobox.set('5')
        else:
            self.combobox = ttk.Combobox(self.input_name_win, state='readonly', values=['3', '4'])
            self.combobox.set('3')

        button = ttk.Button(self.input_name_win, text='Продолжить', command=self.reg_onu_validation)
        button.place(x=100, y=130, width=200, height=40)

        self.combobox.place(x=140, y=50)

    def reg_onu_validation(self):
        if applib.name_onu_validation(self.entry_reg.get()):

            vlan_id = self.combobox.get()

            self.labels2[4]['text'] = f'Введённое имя: [{self.entry_reg.get()}]'
            self.labels2[5]['text'] = f'Подтверждение регистрации ONU на порту...'

            line_srv_profile = '100'
            if vlan_id == '3':
                line_srv_profile = '103'

            self.ssh.send_data(f'ont confirm {self.searched_port} all sn-auth omci ont-lineprofile-id {line_srv_profile} ont-srvprofile-id {line_srv_profile} desc "{self.entry_reg.get()}"\n')
            self.ssh.send_data('\n\n\n')

            self.vlan_id = vlan_id
            self.input_name_win.destroy()
            self.auto_reg_win.grab_set()

            self.after(1500, self.reg_reg_onu)

        else:
            tk.messagebox.showwarning('Имя не прошло проверку',
                                      'Допустимые символы [0-9, A-Z, a-z, _ / ( ) -]\n\n'
                                      'Длина имени: от 6 до 35 символов\n\nНе должно быть пробелов',
                                      parent=self.input_name_win)

    def reg_reg_onu(self):
        out = self.ssh.receive_data()
        if out is not False:
            self.result += out
            self.after(1500, self.reg_reg_onu)
        else:

            self.reg_id_ont = applib.check_registration_ont(self.result)
            if self.reg_id_ont is False:
                tk.messagebox.showerror('Ошибка', 'Не удалось получить ответ после регистрации ONU\nвозможно из за потери пакетов\nили неизветсной ошибки', parent=self.auto_reg_win)
            else:
                self.labels2[6]['text'] = f'ONU получила ID номер: {self.reg_id_ont}'
                self.labels2[7]['text'] = f'Поиск свободного сервис-порта...'

                self.ssh.send_data('quit\n')
                self.ssh.send_data('\n')
                self.ssh.send_data('display service-port next-free-index\n')
                self.ssh.send_data('\n')

                self.after(1500, self.reg_service_port)
                self.result = ''

    def reg_service_port(self):
        out = self.ssh.receive_data()
        if out is not False:
            self.result += out
            self.after(1500, self.reg_service_port)
        else:
            service_port = applib.search_next_free_index(self.result)
            if service_port is not False:

                self.labels2[8]['text'] = f'Сервис-порт успешно найден, номер: {service_port}'
                if self.selected_gpon == 'garage':
                    vlan = self.vlan5
                else:
                    vlan = self.vlan_id
                self.ssh.send_data(f'service-port {service_port} vlan {vlan} gpon 0/1/{self.searched_port} ont {self.reg_id_ont} gemport 11 multi-service user-vlan {vlan} tag-transform translate\n')
                self.ssh.send_data('\n\n\n')
                self.labels2[9]['text'] = f'VLAN_id [{vlan}] успешно назначен.'
                self.vlan_id = ''
                self.labels2[10]['text'] = f'Привязка сервис-порта к ONU выполнена.'
                self.labels2[11]['text'] = f'Регистрация завершена'

                if tk.messagebox.askyesno('Сохранить конфигурацию', 'Сохранить внесённые изменения?', parent=self.auto_reg_win):
                    self.ssh.send_data('quit\n')
                    self.ssh.send_data('save\n')
                    self.ssh.send_data('\n\n\n')
                    self.ssh.send_data('config\n')
                    self.ssh.send_data('int gpon 0/1\n')

                    self.labels2[11]['text'] = f'Сохранение изменений.. подождите 3 сек..'
                    self.after(3000, self.reg_finally)
                else:
                    self.ssh.send_data('int gpon 0/1\n')
                    self.auto_reg_win.destroy()
            else:
                self.ssh.send_data('int gpon 0/1\n')
                tk.messagebox.showerror('Ошибка', 'Неизвестная ошибка', parent=self.auto_reg_win)
                self.auto_reg_win.destroy()

    def reg_finally(self):
        self.labels2[12]['text'] = f'Сохранение изменений завершено.'
        self.after(3000, self.auto_reg_win.destroy)


    def create_delete_onu_win(self):
        self.result = ''
        # проверка выбран ли элемент(онушка)
        # если нет, то вывести сообщение об этом

        self.item = self.tree.focus()
        self.item = self.item.split(',')
        if self.item[0] == 'onu':
        #self.item = ['onu', 2, 10, 'name124']

            self.flag = tk.messagebox.askyesno('Удалить ONU', f'Вы уверены что хотите удалить ONU?\nПорт: {self.item[1]}\nID: {self.item[2]}\nИмя: {self.item[3]}')

            if self.flag:

                self.delete_onu_win = tk.Toplevel(self, bg='grey20')
                self.delete_onu_win.grab_set()

                # центровка открывшегося окна
                screen_width = self.winfo_screenwidth()
                screen_height = self.winfo_screenheight()
                win_width, win_height = 500, 300
                x_coordinate = int((screen_width / 2) - (win_width / 2))
                y_coordinate = int((screen_height / 2) - (win_height / 2))
                self.delete_onu_win.geometry(f"{win_width}x{win_height}+{x_coordinate}+{y_coordinate}")
                self.delete_onu_win.title("Удалить ONU")  # подпись окна

                self.delete_onu_win.protocol('WM_DELETE_WINDOW', lambda :tk.messagebox.showerror('Так делать не надо', 'Дождитесь завершения работы алгоритма', parent=self.delete_onu_win))


                self.labels1 = [tk.Label(self.delete_onu_win, fg='#00FF7F', font='arial 13 bold', bg='grey20') for _ in range(13)]

                y = 0
                for i in self.labels1:
                    i.place(x=10, y=y)
                    y += 20

                self.labels1[0]['text'] = 'Удаление ONU...'
                self.labels1[1]['text'] = 'Отправка комманд на GPON блок..'

                self.ssh.send_data('quit\n')
                self.ssh.send_data('\n')
                self.ssh.send_data('display service-port all\n')
                self.ssh.send_data('\n\n\n')
                self.ssh.send_data('                          \n')
                self.ssh.send_data('\n')

                self.labels1[2]['text'] = 'Отправка комманд завершена'
                self.after(1000, self.deleting_onu)

        else:
            tk.messagebox.showwarning('ONU не выбрана', 'Выберите из списка ONU\nкоторую хотите удалить')



    def deleting_onu(self):

        self.labels1[3]['text'] = 'Запись байтов ответа GPON блока в буфер...'
        out = self.ssh.receive_data()
        if out is not False:
            self.result += out
            self.after(1500, self.deleting_onu)
        else:
            self.labels1[4]['text'] = 'Запись в буфер завершена'
            self.labels1[5]['text'] = 'Поиск сервис-порта ONU...'
            service_port = applib.search_service_port(self.result, self.item[1], self.item[2])

            if service_port:
                self.ssh.send_data(f'undo service-port {service_port}\n')
                self.ssh.send_data(f'\n\n\n')
                self.ssh.send_data(f'int gpon 0/1\n')
                self.labels1[6]['text'] = f'Сервис-порт [{service_port}] найден и удалён'
                self.labels1[7]['text'] = f'Удаление регистрации ONU...'
                self.ssh.send_data(f'ont delete {self.item[1]} {self.item[2]}\n')
                self.result = ''
                self.after(1500, self.deleting_onu_1)
            else:
                self.ssh.send_data(f'\n\n\n')
                self.ssh.send_data(f'int gpon 0/1\n')
                tk.messagebox.showerror('Ошибка удаления', 'Не удалось найти сервис-порт')
                self.delete_onu_win.destroy()


    def deleting_onu_1(self):
        out = self.ssh.receive_data()
        if out is not False:
            self.result += out
            self.after(1500, self.deleting_onu_1)
        else:
            del_onu = applib.check_deleted_ont(self.result)
            if del_onu == 'ont deleted':
                self.labels1[8]['text'] = 'Удаление завершено успешно.'
                self.labels1[9]['text'] = 'Обновление списка ONU...'
                self.insert_list_onu(port_=f'port {self.item[1]}')
                self.labels1[10]['text'] = 'Обновление списка завершено.'
                if tk.messagebox.askyesno('Сохранение конфигурации', 'Сохранить внесённые изменения?', parent=self.delete_onu_win):
                    self.ssh.send_data('quit\n\n')
                    self.ssh.send_data('quit\n\n')
                    self.ssh.send_data('save\n\n')
                    self.ssh.send_data('\n')
                    self.ssh.send_data('config\n')
                    self.ssh.send_data('int gpon 0/1\n')
                    self.ssh.send_data('\n\n\n')

                    self.labels1[11]['text'] = 'Сохранение конфигурации.. подождите 3 сек.'
                    self.after(3000, self.deleting_finaly)
                else:
                    self.delete_onu_win.destroy()

            elif del_onu == 'error':
                self.labels1[8]['fg'] = '#FFA500'
                self.labels1[8]['text'] = 'Удаление завершено с ошибками.'
                self.after(3000, self.delete_onu_win.destroy)
            else:
                self.labels1[8]['fg'] = 'red'
                self.labels1[8]['text'] = 'Ошибка.'
                self.after(3000, self.delete_onu_win.destroy)

    def deleting_finaly(self):
        self.labels1[12]['text'] = 'Сохранение выполнено.'
        self.after(3000, self.delete_onu_win.destroy)




    def open_monitoring_window(self):
        self.count = 0
        self.flag = True
        #проверка выбран ли элемент(онушка)
        #если нет, то вывести сообщение об этом
        self.item = self.tree.focus()
        self.item = self.item.split(',')
        if self.item[0] == 'onu':

            # открытие самого окна и блокировка основного
            self.toplevel_win = tk.Toplevel(self)
            self.toplevel_win.grab_set()

            # центровка открывшегося окна
            screen_width = self.winfo_screenwidth()
            screen_height = self.winfo_screenheight()
            win_width, win_height = 700, 500
            x_coordinate = int((screen_width / 2) - (win_width / 2))
            y_coordinate = int((screen_height / 2) - (win_height / 2))
            self.toplevel_win.geometry(f"{win_width}x{win_height}+{x_coordinate}+{y_coordinate}")
            self.toplevel_win.title("Автомониторинг выбранной ONT") #подпись окна

            # таблица вывода сигнала ONU
            columns = ('iteration', 'name', 'signal')
            self.monitoring_table = ttk.Treeview(self.toplevel_win, show="headings", columns=columns, height=20)
            self.monitoring_table.column('iteration', width=5)
            self.monitoring_table.column('name', width=200)
            self.monitoring_table.column('signal', width=50)
            self.monitoring_table.heading('iteration', text='Отправлено запросов')
            self.monitoring_table.heading('name', text='Имя ONU')
            self.monitoring_table.heading('signal', text='Сигнал ONU')
            self.monitoring_table.place(x=10, y=10, width=650)

            # маркировка по цветам в таблице
            self.monitoring_table.tag_configure('online', background='#7CFC00')
            self.monitoring_table.tag_configure('offline', background='red', foreground='white')

            # скроллбор для таблицы
            scrollbar = ttk.Scrollbar(self.toplevel_win, orient='vertical', command=self.monitoring_table.yview)
            scrollbar.place(x=665, y=10, height=425)
            self.monitoring_table.configure(yscroll=scrollbar.set)

            # надписи с инфой какая онушка и порт выбранны
            label1 = tk.Label(self.toplevel_win, text=f'НОМЕР ПОРТА: {self.item[1]}', font='arial 10 bold')
            label2 = tk.Label(self.toplevel_win, text=f'НОМЕР ONU: {self.item[2]}', font='arial 10 bold')
            label3 = tk.Label(self.toplevel_win, text=f'ИМЯ ONU: {self.item[3]}', font='arial 10 bold')
            label1.place(x=10, y=450)
            label2.place(x=150, y=450)
            label3.place(x=300, y=450)

            self.after(1000, self.auto_monitoring) # вызов через 1 сек

            # если окно пытаются закрываеть, то меняется флаг
            self.toplevel_win.protocol('WM_DELETE_WINDOW', self.false_flag)

        else:
            tk.messagebox.showwarning('ONU не выбрана', 'Выберите из списка ONU\nсигнал которой нужно выводить')

    def false_flag(self):
        # изменение флага на False
        self.flag = False

    def auto_monitoring(self):
        # отправка комманд вывода оптической инфы и вызов метода записи ответа gpon блока

        self.ssh.send_data(f'display ont optical-info {self.item[1]} {self.item[2]}\n')
        self.ssh.send_data(f' \n')

        self.after(1000, self.auto_monitoring_recv) # вызов через 1 сек

    def auto_monitoring_recv(self):
        # циклический метод вызывающий сам себя
        out = self.ssh.receive_data()
        if out is not False:
            self.result += out
            self.after(500, self.auto_monitoring_recv)

        else:
            # если запись закончилась, тогда проверить флаг
            if self.flag:
                self.count += 1
                signal = applib.search_ont_signal(self.result)

                if signal is False:
                    self.monitoring_table.insert('', tk.END, values=[self.count,f'{self.item[3]}','НЕТ СВЯЗИ'], tags=('offline',))
                else:
                    self.monitoring_table.insert('', tk.END, values=[self.count,f'{self.item[3]}',f'{signal}'], tags=('online',))
                self.after(100, self.auto_monitoring)
                self.result = ''
                self.after(50, lambda :self.monitoring_table.yview(tk.SCROLL, 1, tk.PAGES))

            else:
                # если флаг на False, тогда закрыть окно и очистить 'result'
                self.result = ''
                self.toplevel_win.destroy()
                self.flag = True # перевод флага на True после закрытия, чтобы другие онушки можно было тоже мониторить

    def press_start_btn(self):
        # функция привязана к нажатию кнопки запуска
        # парсинга онушек и их данных
        # пока идёт процесс остальные виджеты должны быть заблокированы
        # очистака буфера 'result' и списка 'LIST' для надёжности и для того,
        # чтобы после предыдущих парсингов в нём ничего не оставалось
        self.result = ''
        self.LIST = []
        self.result_optical = ''
        self.result_dist = ''

        self.disable_all_widgets()  #откл. все виджеты, чтобы никто не нажимал кнопки
        self.number_port = self.radio_button_var.get() #получить номер выбранного порта

        # отправка комманд на gpon блок
        self.ssh.send_data(f'display ont info {self.number_port} all\n')
        self.ssh.send_data('          \n')

        self.txt_progress.set('/gpon/send_cmd')
        self.progress.step(20)

        # запуск циклического метода записи в буфер 'result'
        # и формирование списка
        self.after(300, self.parsing_first_info)

        self.txt_progress.set('/gpon/запись байтов')
        self.progress.step(10)

    def parsing_first_info(self):
        # метод считывает sn,name,id,status
        # формирует LIST, набивает 'result'
        # и запускает след. метод: parsing_optical_info

        # цикл набивания символами буфера 'result'

        out = self.ssh.receive_data()
        if out is not False:
            self.result += out
            self.progress.step(10)
            self.after(300, self.parsing_first_info) # задержка 0.3 секунды, для корректности работы ssh

            # как только gpon блок завершил передавать данные
            # начинается формирование первичного вложенного списка
        else:
            # поиск id,name,sn,status в буфере 'result'
            self.id_onu = applib.parsed_id(self.result)
            self.name_onu = applib.parsed_name(self.result)
            self.sn_onu = applib.parsed_sn(self.result)
            self.status_onu = applib.parsed_status(self.result)

            self.txt_progress.set('/gpon/создание таблицы')
            self.progress.step(20)

            # если на порту не будет онушек, то id_onu будет пуст,
            # тогда вывести messagebox о том что порт пуст и
            # далее включить обратно все виджеты
            if self.id_onu is False:
                self.txt_progress.set('gpon ERROR')

                tk.messagebox.showwarning(f'PORT: {self.number_port}', f'На выбранном порту не найдено ONT')
                self.enable_all_widgets() #вкл. все виджеты

                self.txt_progress.set('')

            else:
                # создание вложенного списока превичной инфы: sn,id,name,status
                for i in range(len(self.id_onu)):
                    self.LIST.append([self.id_onu[i],
                                      self.name_onu[i],
                                      self.sn_onu[i],
                                      self.status_onu[i]])

                self.insert_in_table(self.LIST) #заполнить таблицу данными из списка LIST

                # передача эстафеты след.методам
                # проверка чек-бокса вовыда оптических сигналов
                if self.check_btn_var.get():
                    self.send_data_optical()  # этот метод отправляет команды на gpon и вызывает метод parsing_optical_info()

                # проверка чек-бокса вовыда дистанций
                elif self.check_btn_var1.get():
                    self.send_data_distance()  # запускается если чек-бокс метода parsing_optical_info() отключен

                else:
                    # если чек-боксы не выбраны, тогда ничего не делать
                    # и вкл. обратно все виджеты
                    self.enable_all_widgets()
                    self.txt_progress.set('')

            self.progress.stop()

    def send_data_optical(self):
        # отправляет запросы на получение инфы об оптических сигналах
        # и через 1 секунд вызвает метод parsing_optical_info
        # который в начале в цикле принимает инфу, а после ДОБАВЛЯЕТ В СПИСОК "LIST"
        # СИГНАЛЫ
        self.txt_progress.set('/gpon/отправка комманд/')

        for i in self.id_onu:
            self.ssh.send_data(f'display ont optical-info {self.number_port} {i}\n')
            self.ssh.send_data(' \n')
            print(i)

        self.after(1000, self.parsing_optical_info)  # вызов метода через 1 сек



    def parsing_optical_info(self):
        # метод парсинга сигналов каждой онушки
        # найденые значения записывает во вложенный список LIST
        # и запускает след. метод: send_data_distance() (парсинг дистанций)

        # цикл наполнения буфера 'result_optical'
        out = self.ssh.receive_data()

        # кусок кода наполнения progressBar
        pr_count = applib.search_ont_signal_(str(out))
        step = 100 / len(self.id_onu)
        self.progress.step(step*pr_count)
        self.progress_counter += pr_count
        self.txt_progress.set(f'Обработка сигналов/onu/{self.progress_counter}') #вывод текста рядом с прогрессбаром

        if out is not False:
            self.result_optical += out
            self.after(1500, self.parsing_optical_info)
        else:
            # после того как все символы набились в буфер, разделить строку 'result_optical'
            # на более мелкие подстроки
            splited_result = self.result_optical.splitlines()
            local_list = []

            # алгоритм перебора и поиска инфы о сигналах
            for substring in splited_result:
                online_onu = applib.search_ont_signal(substring)
                offline_onu = applib.search_ont_offline(substring)

                if online_onu is not False:
                    local_list.append(online_onu)  # добавить сигнал в список

                if offline_onu is not False:
                    local_list.append(offline_onu)  # добавить '0' если нет сигнала

            # если длина LIST (кол-во ONT) и длина local_list (сигналы каждой ONT) НЕ совпадают
            if len(self.LIST) != len(local_list):

                # тогда прекратить процесс и вывести оповещение об этом
                tk.messagebox.showerror('Ошибка', 'Не удалось получить список сигналов\nиз за потери пакетов в сети')
                self.enable_all_widgets()  # вкл. все виджеты
                self.ssh.send_data('   \n')  # корректировка ssh терминала (для норм.парсинга в будущем)
            else:
                # иначе если всё нормально (LIST и local_list совпадают)
                # тогда добавить сигналы в общий вложенный список LIST
                for i in range(len(self.LIST)):
                    self.LIST[i].append(local_list[i])

                # вставить инфу и сигналы в таблицу (из LIST), mode='tag' передаётся для того
                # чтобы метод insert_in_table() выполнил цветовую маркировку в таблице
                self.insert_in_table(self.LIST, mode='tag')

                # проверка чек_бокса метода парсинга дистанций
                if self.check_btn_var1.get():
                    self.send_data_distance() # вызов метода отправки комманд на получение дистанций
                else:
                    self.enable_all_widgets()  # вкл. все виджеты

            self.progress.stop()  # очистить progressBar
            self.progress_counter = 0 #очистить счётчик прогресса
            self.txt_progress.set('') #очистить текст прогресса

    def send_data_distance(self):
        # метод набивания символами буфера 'relust_dist'
        self.txt_progress.set('/gpon/отправка комманд/')

        for i in self.id_onu:
            self.ssh.send_data(f'display ont info {self.number_port} {i}\n')
            self.ssh.send_data('q\n')

        self.after(1000, self.parsing_dist_info) # запустить метод через 1 сек

    def parsing_dist_info(self):
        # метод парсинга дистанций онушек
        out = self.ssh.receive_data()

        # кусок кода наполнения progressBar
        pr_count = applib.parsed_onu_distance_(str(out))
        step = 100 / len(self.id_onu)
        self.progress.step(step * pr_count)
        self.progress_counter += pr_count
        self.txt_progress.set(f'Обработка дистанций/onu/{self.progress_counter}')  # вывод текста рядом с прогрессбаром

        if out is not False:
            self.result_dist += out
            self.after(1500, self.parsing_dist_info)
        else:
            dist_list = applib.parsed_onu_distance(self.result_dist)
            if len(dist_list) != len(self.LIST): # проверка потерялась где-гибудь хоть одна дистанция
                tk.messagebox.showerror('Ошибка', 'Не удалось получить список дистанций\nиз за потери пакетов в сети')

            else:
                for i in range(len(self.LIST)):
                    if self.check_btn_var.get() is False:
                        self.LIST[i].append(0) #заглушка на место сигналов в виде Нуля, на тот случай если не выбран парсинг сигналов

                    self.LIST[i].append(dist_list[i]) #добавление дистанций в LIST

                    if self.check_btn_var.get(): #если режим парсинга сигналов выбран, то mode='tag' (маркирует по цветам)
                        mode = 'tag'
                    else:
                        mode = None
                    self.insert_in_table(self.LIST, mode)

            self.enable_all_widgets() # вкл. все виджеты
            self.progress.stop()  # очистить progressBar
            self.progress_counter = 0  # очистить счётчик прогресса
            self.txt_progress.set('')  # очистить текст прогресса

    def check_signals(self):
        # метод проверки есть ли сигналы в LIST

        for i in self.LIST:
            if i[4] != '': #если есть, тогда включить мод маркировки
                return True
        return False


    def sort_table(self, func):
        # метод сортировки информации в таблице

        self.LIST.sort(key=func) # сортировка

        if self.check_signals(): # маркировать по цвету или нет
            self.insert_in_table(self.LIST, mode='tag')
        else:

            self.insert_in_table(self.LIST)



    def insert_in_table(self, info_lst, mode=None):
        # метод добавления списка ONU, их name, id, и т.д
        # выполняет расскраску по цветам, в зависимости от сигнала
        # если маркировку по цветам не нужно делать, тогда в mode ничего не передавать

        # удалить предыдущие записи в таблице
        for i in self.table.get_children():
            self.table.delete(i)

        # проверка передали ли в mode ключевую строку 'tag'
        # если да, тогда выполнять маркировку по цветам
        if mode == 'tag':
            for i in info_lst:

                if i[4] == 0:
                    self.table.insert('', tk.END, values=i, tags=('offline',))
                elif -29 <= i[4] <= -27.01:
                    self.table.insert('', tk.END, values=i, tags=('low_sig',))
                elif i[4] <= -29.01:
                    self.table.insert('', tk.END, values=i, tags=('bad_sig',))
                elif -27 <= i[4]:
                    self.table.insert('', tk.END, values=i, tags=('norm_sig',))


                self.table.tag_configure('norm_sig', background='#7CFC00')
                self.table.tag_configure('low_sig', background='#FFC125')
                self.table.tag_configure('bad_sig', background='#CD2626')
                self.table.tag_configure('bad_sig', foreground='white')
                self.table.tag_configure('offline', background='#919192')

        else:
            # иначе если mode=None, тогда вставить инфу без маркировки цветовой
            for i in info_lst:
                self.table.insert('', tk.END, values=i)



    def fixed_map(self, option):
        # функция исправления бага tkinter
        return [elm for elm in self.style.map("Treeview", query_opt=option)
                if elm[:2] != ("!disabled", "!selected")]



    def disable_all_widgets(self):
        # функция отключения почти всех виджетов

        items = self.menu_widgets.winfo_children()
        for i in items:
            i['state'] = tk.DISABLED

        items = self.radio_button_frame.winfo_children()
        for i in items:
            i['state'] = tk.DISABLED

    def enable_all_widgets(self):
        # функция включение почти всех виджетов
        items = self.menu_widgets.winfo_children()
        for i in items:
            i['state'] = tk.NORMAL

        items = self.radio_button_frame.winfo_children()
        for i in items:
            i['state'] = tk.NORMAL

    def delete_info_optical_default(self):
        for i in range(7):
            self.labels_info[i]['text'] = ''
            self.labels_info_default[i]['text'] = ''
            self.labels_info[i]['bg'] = 'grey94'
            self.labels_info[i]['fg'] = 'black'

    def insert_list_onu(self, event=None, port_=None, id_=None):
        window = BlockWindow(self, 800, 450)
        window.grab_set()
        self.update()

        item_tree = ''
        if port_ is None:
            item = self.tree.focus()
            print(item)
        else:
            item = port_

        if item[:4] == 'port':
            number_port = item[5:]

            window.insert_text('Запрос на получение списка ONU отправлен')
            self.update()
            self.ssh.send_data(f'display ont info {number_port} all\n')
            self.ssh.send_data('             \n')

            result = ''
            count = 0
            s = '.'
            while True:
                time.sleep(0.3)
                recv = self.ssh.receive_data()
                window.insert_text(f'Сбор информации о списке ONU{s*count}')
                self.update()
                if recv is False:
                    break
                result += recv
                count += 1

            list_names = applib.parsed_name(result)
            list_status = applib.parsed_status(result)
            list_id = applib.parsed_id(result)
            window.insert_text('Формирование списка')

            if list_names:
                children = self.tree.get_children(item)
                for count, i in enumerate(children):
                    self.tree.delete(i)
                    if count % 5 == 0:
                        window.insert_text(f'Обновление данных{s * count}')
                        self.update()

                count = 0
                for i in list_names:
                    status = ''
                    if list_status[count] == 'online':
                        status = ' ->'
                    else:
                        status = '     '

                    if list_id[count] == id_:
                        item_tree = f'onu,{number_port},{list_id[count]},{i}'

                    self.tree.insert(item,
                                     iid=f'onu,{number_port},{list_id[count]},{i}',
                                     index=tk.END,
                                     text=f' {status} |  {i}',
                                     image=self.img_1,
                                     tags=('default',))
                    count += 1
                    window.insert_text(f'Добавлена ONU:   {i}')
                    self.update()
                self.tree.tag_configure('     ', foreground='grey70')

                self.update()
                window.destroy()
                return item_tree
        self.update()
        window.destroy()

    def refresh_list_onu(self, element):
        for i in self.tree.get_children(element):
            self.tree.delete(i)

    def select_onu(self, event=None, item=None):
        s = '.'

        self.delete_info_optical_default()
        result = ''
        if item is None:
            item = self.tree.focus()

        item = item.split(',')
        if item[0] == 'onu':
            print('processing')
            number_port, number_onu = item[1], item[2]

            window = BlockWindow(self, 800, 450)
            window.grab_set()
            self.update()

            if self.FLAG_DISPLAY_OPTICAL.get():

                self.ssh.send_data(f'display ont optical info {number_port} {number_onu}\n')
                self.ssh.send_data(f' \n')

                window.insert_text('Запрос на получение информации отправлен')
                self.update()

                count = 0
                while True:
                    time.sleep(0.8)
                    out = self.ssh.receive_data()
                    if out is False:
                        break
                    result += out
                    window.insert_text(f'Сбор информации{s * count}')
                    self.update()
                    count += 1

                lst_info = applib.optical_info_packet(result)
                count = 0
                if lst_info != 'onu offline' and lst_info is not False:
                    signal = float(lst_info[1][0])

                    if -27 <= signal:
                        self.labels_info[1]['bg'] = '#ADFF2F'
                    elif -30 <= signal <= -27.01:
                        self.labels_info[1]['bg'] = '#FFA500'
                        self.labels_info[1]['fg'] = 'black'
                    elif signal <= -30.01:
                        self.labels_info[1]['bg'] = '#FF4500'
                        self.labels_info[1]['fg'] = 'white'

                    # заполнение labels полей иформацией об онушке
                    for c, i in enumerate(lst_info):
                        self.labels_info[count]['text'] = i[0]
                        count += 1
                        print(i[0])
                        window.insert_text(f'Заполнение информационных полей{s * c}')
                        self.update()
                else:
                    # если ONU оффлайн тогда ничего не выводить и очистить поля
                    for i in range(7):
                        self.labels_info[i]['text'] = ''
                        window.insert_text('ONU не в сети')
                        self.update()

            if self.FLAG_DISPLAY_DEFAULT.get():

                self.ssh.send_data(f'display ont info {number_port} {number_onu}\n')
                self.ssh.send_data(' \n')
                self.ssh.send_data('q\n')

                window.insert_text(f'Запрос на получение доп.информации отправлен')
                self.update()

                out = ''
                result = ''
                count = 0
                while True:
                    time.sleep(0.8)
                    out = self.ssh.receive_data()
                    if out is False:
                        break
                    result += out
                    window.insert_text(f'Сбор информации{s * count}')
                    self.update()
                    count += 1

                lst_info = applib.default_info_packet(result)
                count = 0
                if lst_info is not False:
                    for i in lst_info:
                        self.labels_info_default[count]['text'] = i[0]
                        count += 1
                        window.insert_text(f'Заполнение информационных полей{s * count}')
                        self.update()
            self.update()
            window.destroy()

    def global_time(self):
        self.after(self.GLOBAL_TIMER, self.global_time_window)

    def global_time_window(self):
        # таймер который закрывает программу через 10 минут
        # и спрашивает делать ли это или нет

        t_w = TimerWindow(self)
        winsound.PlaySound("SystemHand", winsound.SND_ASYNC) # вызов системного звука windows
        self.global_time()

    def raise_frame(self, frame):
        # метод переключающий фреймы
        frame.tkraise()

    def open_select_onu(self, port=3, id_onu=20, callback=None):
        # метод автоматического выбора порта и ONU из списка
        # грубо говоря имитация будто кто-то нажимает на виджеты

        self.raise_frame(self.main_frame) # переключается на фрейм расширенного режима
        self.FLAG_DISPLAY_OPTICAL.set(True)
        self.FLAG_DISPLAY_DEFAULT.set(True)
        iid_onu = self.insert_list_onu(port_=f'port {port}', id_=id_onu) # возращает iid ONU и заполняет список
        self.tree.focus(iid_onu)  # фокусирутеся на найденой ONU
        self.tree.selection_set(iid_onu)  # выбирает найденую ONU
        self.tree.see(iid_onu)  # проматыет список (древо) до места, где присутсвуте ONU

        self.after(1000, lambda: self.FLAG_DISPLAY_DEFAULT.set(False))
        self.after(1000, lambda: callback())


    def search_sn_win(self):
        SearchSnWin(self)


    def start(self):
        # метод условной точки входа в программу

        user, passw, ip = self.target_connection

        try:
            self.ssh = applib.ClientSSH(user, passw, ip)
        except paramiko.ssh_exception.SSHException:
            tk.messagebox.showerror('Ошибка аутентификации', 'Не удалось авторизоваться при подключении:\n\n1) другой пользователь не вышел с GPON блока\n\n2) неверные логин или пароль')
            sys.exit()
        except Exception:
            tk.messagebox.showerror('ОШИБКА', 'Неизвестная ошибка, перезапустите программу')
            sys.exit()

        self.title(f'Сессия установлена с {self.target_connection[2]}')
        self.deiconify()
        self.global_time() # когда открывается глав.окно запускается таймер


if __name__ == '__main__':
    app = MainWin()
    app.mainloop()
else:
    app = MainWin()
    app.mainloop()
    