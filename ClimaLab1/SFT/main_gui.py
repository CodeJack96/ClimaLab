import sys, socket, serial, serial.tools.list_ports
from PyQt5 import QtWidgets, QtCore, QtGui
from datetime import datetime
from openpyxl import Workbook
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


# ===================== VENTANA WIFI =====================
class WiFiDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configurar WiFi")
        self.setFixedSize(400, 280)

        self.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #6A1B9A, stop:1 #4A148C);
                border-radius: 12px;
            }
            QLabel { 
                font-size: 14px; 
                color: white;
                font-weight: bold;
            }
            QLineEdit { 
                font-size: 14px; 
                padding: 10px;
                border-radius: 8px;
                border: 2px solid #D1C4E9;
                background: white;
            }
            QPushButton {
                font-size: 14px;
                padding: 12px;
                border-radius: 10px;
                background: #FF9800;
                color: white;
                font-weight: bold;
                border: none;
            }
            QPushButton:hover {
                background: #F57C00;
            }
            QPushButton:pressed {
                background: #E65100;
            }
        """)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(25, 25, 25, 25)

        title = QtWidgets.QLabel("⚙️ Configurar WiFi")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: white;")
        title.setAlignment(QtCore.Qt.AlignCenter)
        
        self.ssid = QtWidgets.QLineEdit()
        self.ssid.setPlaceholderText("Nombre de la red WiFi")
        self.ssid.setStyleSheet("padding: 12px;")
        
        self.password = QtWidgets.QLineEdit()
        self.password.setPlaceholderText("Contraseña")
        self.password.setEchoMode(QtWidgets.QLineEdit.Password)
        self.password.setStyleSheet("padding: 12px;")

        eye_btn = QtWidgets.QToolButton()
        eye_btn.setText("👁")
        eye_btn.setCheckable(True)
        eye_btn.setStyleSheet("""
            QToolButton {
                font-size: 16px;
                background: #E1BEE7;
                border-radius: 5px;
                padding: 8px;
                min-width: 40px;
            }
            QToolButton:hover { background: #D1C4E9; }
        """)
        eye_btn.toggled.connect(self.toggle_password)

        pass_layout = QtWidgets.QHBoxLayout()
        pass_layout.addWidget(self.password)
        pass_layout.addWidget(eye_btn)

        btn_ok = QtWidgets.QPushButton("💾 Guardar Configuración")
        btn_ok.clicked.connect(self.accept)

        layout.addWidget(title)
        layout.addSpacing(15)
        layout.addWidget(QtWidgets.QLabel("📶 SSID:"))
        layout.addWidget(self.ssid)
        layout.addWidget(QtWidgets.QLabel("🔑 Contraseña:"))
        layout.addLayout(pass_layout)
        layout.addSpacing(20)
        layout.addWidget(btn_ok)

    def toggle_password(self, checked):
        self.password.setEchoMode(QtWidgets.QLineEdit.Normal if checked else QtWidgets.QLineEdit.Password)

    def get_data(self):
        return self.ssid.text(), self.password.text()


# ===================== TARJETA DE DATOS =====================
class DataCard(QtWidgets.QFrame):
    def __init__(self, title, icon="", color="#6A1B9A"):
        super().__init__()
        self.setMinimumHeight(150)
        self.setMaximumHeight(170)
        
        self.setStyleSheet(f"""
            QFrame {{
                background: white;
                border-radius: 15px;
                border: 2px solid {color};
            }}
            QLabel#title {{ 
                font-size: 15px; 
                color: {color};
                font-weight: bold;
                padding: 5px;
            }}
            QLabel#value {{ 
                font-size: 26px; 
                font-weight: bold; 
                color: {color};
                padding: 10px;
            }}
        """)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        title_layout = QtWidgets.QHBoxLayout()
        
        if icon:
            icon_label = QtWidgets.QLabel(icon)
            icon_label.setStyleSheet("font-size: 22px;")
            title_layout.addWidget(icon_label)
        
        self.name = QtWidgets.QLabel(title)
        self.name.setObjectName("title")
        title_layout.addWidget(self.name)
        title_layout.setAlignment(QtCore.Qt.AlignCenter)
        
        self.value = QtWidgets.QLabel("Sensor no detectado")
        self.value.setObjectName("value")
        self.value.setAlignment(QtCore.Qt.AlignCenter)

        layout.addLayout(title_layout)
        layout.addWidget(self.value)

    def set_value(self, text):
        self.value.setText(text)


# ===================== APP PRINCIPAL =====================
class EstacionApp(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        
        # Variables de estado
        self.serial_conn = None
        self.sock = None
        self.wifi_configured = False  # Ya no es obligatorio
        self.conn_mode = "Serial"
        self.measuring = False
        self.wifi_ip = "192.168.4.1"  # IP por defecto de ESP32 en modo AP
        self.wifi_port = 3333
        
        # Datos
        self.data_log = []
        self.uv_data, self.temp_data, self.hum_data, self.pres_data = [], [], [], []
        
        # Timers
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.read_data)
        
        self.end_timer = QtCore.QTimer()
        self.end_timer.timeout.connect(self.stop_measurement)
        
        # Configurar UI
        self.setup_ui()
        
        # Inicializar lista de puertos
        QtCore.QTimer.singleShot(100, self.refresh_ports_list)

    def setup_ui(self):
        self.setWindowTitle("Estación de Monitoreo")
        self.resize(1150, 750)

        # Estilos optimizados pero atractivos
        self.setStyleSheet("""
            QWidget { 
                background: #F5F5F5;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QPushButton {
                background: #6A1B9A;
                color: white;
                font-size: 13px;
                padding: 11px;
                border-radius: 8px;
                border: none;
                font-weight: bold;
            }
            QPushButton:hover { background: #7B1FA2; }
            QPushButton:pressed { background: #4A148C; }
            QPushButton:disabled { 
                background: #D1C4E9; 
                color: #757575;
            }
            QComboBox, QSpinBox {
                padding: 8px;
                border-radius: 6px;
                border: 2px solid #D1C4E9;
                background: white;
                font-size: 13px;
                min-height: 36px;
            }
            QComboBox:hover, QSpinBox:hover {
                border: 2px solid #9C27B0;
            }
            QLabel { 
                font-size: 13px; 
                color: #424242;
            }
        """)

        # Layout principal
        main_layout = QtWidgets.QHBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        # Panel izquierdo (datos y gráficos)
        left_panel = QtWidgets.QVBoxLayout()
        left_panel.setSpacing(15)

        # Título
        title = QtWidgets.QLabel("🌤️ Estación de Monitoreo Ambiental")
        title.setStyleSheet("""
            font-size: 24px; 
            font-weight: bold; 
            color: #4A148C;
            padding: 15px;
            background: white;
            border-radius: 12px;
            border: 2px solid #BA68C8;
        """)
        title.setAlignment(QtCore.Qt.AlignCenter)
        left_panel.addWidget(title)

        # Tarjetas de datos con colores específicos
        grid = QtWidgets.QGridLayout()
        grid.setSpacing(15)
        grid.setContentsMargins(5, 5, 5, 5)
        
        self.cards = {
            "UV": DataCard("Índice UV", "☀️", "#FF9800"),
            "Temp": DataCard("Temperatura", "🌡️", "#2196F3"),
            "Hum": DataCard("Humedad", "💧", "#00BCD4"),
            "Pres": DataCard("Presión", "📊", "#9C27B0")
        }
        
        grid.addWidget(self.cards["UV"], 0, 0)
        grid.addWidget(self.cards["Temp"], 0, 1)
        grid.addWidget(self.cards["Hum"], 1, 0)
        grid.addWidget(self.cards["Pres"], 1, 1)
        
        left_panel.addLayout(grid)

        # Selector de gráfico
        graph_label = QtWidgets.QLabel("📈 Visualización de Gráficos:")
        graph_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #6A1B9A;")
        left_panel.addWidget(graph_label)
        
        self.graph_selector = QtWidgets.QComboBox()
        self.graph_selector.addItems(["Índice UV", "Temperatura", "Humedad", "Presión", "Todas las Variables"])
        self.graph_selector.setStyleSheet("padding: 10px; font-size: 14px;")
        self.graph_selector.currentIndexChanged.connect(self.update_graph)
        left_panel.addWidget(self.graph_selector)

        # Gráfico
        self.figure = Figure(figsize=(7, 3.5), facecolor='white', dpi=90)
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setMinimumHeight(280)
        self.canvas.setMaximumHeight(320)
        self.canvas.setStyleSheet("""
            border-radius: 10px;
            border: 2px solid #D1C4E9;
            background: white;
        """)
        self.ax = self.figure.add_subplot(111)
        self.ax.set_facecolor('#FAFAFA')
        self.ax.grid(True, linestyle='--', alpha=0.4, linewidth=0.5)
        left_panel.addWidget(self.canvas)

        # Panel derecho (controles)
        right_panel = QtWidgets.QFrame()
        right_panel.setStyleSheet("""
            QFrame { 
                background: white;
                border-radius: 15px;
                border: 2px solid #BA68C8;
            }
        """)
        
        right_layout = QtWidgets.QVBoxLayout(right_panel)
        right_layout.setContentsMargins(20, 20, 20, 20)
        right_layout.setSpacing(12)

        # Sección Conexión
        conn_label = QtWidgets.QLabel("🔗 CONEXIÓN")
        conn_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #6A1B9A;")
        right_layout.addWidget(conn_label)

        # Modo - MODIFICADO: No obliga a configurar WiFi primero
        right_layout.addWidget(QtWidgets.QLabel("📡 Modo de Comunicación:"))
        self.mode_box = QtWidgets.QComboBox()
        self.mode_box.addItems(["Serial", "WiFi"])
        self.mode_box.currentTextChanged.connect(self.mode_changed)
        right_layout.addWidget(self.mode_box)

        # Configuración WiFi (solo si se selecciona Serial)
        self.wifi_config_frame = QtWidgets.QFrame()
        wifi_config_layout = QtWidgets.QVBoxLayout(self.wifi_config_frame)
        wifi_config_layout.setContentsMargins(0, 5, 0, 5)
        
        wifi_ip_layout = QtWidgets.QHBoxLayout()
        wifi_ip_layout.addWidget(QtWidgets.QLabel("IP ESP32:"))
        self.wifi_ip_input = QtWidgets.QLineEdit("192.168.4.1")
        self.wifi_ip_input.setPlaceholderText("IP de la ESP32")
        wifi_ip_layout.addWidget(self.wifi_ip_input)
        
        wifi_port_layout = QtWidgets.QHBoxLayout()
        wifi_port_layout.addWidget(QtWidgets.QLabel("Puerto:"))
        self.wifi_port_input = QtWidgets.QLineEdit("3333")
        self.wifi_port_input.setPlaceholderText("Puerto")
        wifi_port_layout.addWidget(self.wifi_port_input)
        
        wifi_config_layout.addLayout(wifi_ip_layout)
        wifi_config_layout.addLayout(wifi_port_layout)
        
        # Puerto Serial
        right_layout.addWidget(QtWidgets.QLabel("🔌 Puerto Serial (solo modo Serial):"))
        self.port_box = QtWidgets.QComboBox()
        self.port_box.setMinimumWidth(220)
        self.port_box.setStyleSheet("font-family: 'Consolas', monospace;")
        right_layout.addWidget(self.port_box)

        # Botón WiFi (solo visible en modo Serial)
        self.btn_wifi = QtWidgets.QPushButton("⚙️ Configurar WiFi de ESP32")
        self.btn_wifi.clicked.connect(self.configure_wifi)
        right_layout.addWidget(self.btn_wifi)

        right_layout.addSpacing(10)

        # Separador
        separator = QtWidgets.QFrame()
        separator.setFrameShape(QtWidgets.QFrame.HLine)
        separator.setStyleSheet("background-color: #D1C4E9; height: 2px;")
        right_layout.addWidget(separator)

        # Sección Medición
        measure_label = QtWidgets.QLabel("⏱️ CONFIGURACIÓN DE MEDICIÓN")
        measure_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #6A1B9A;")
        right_layout.addWidget(measure_label)

        # Duración
        duration_layout = QtWidgets.QHBoxLayout()
        duration_layout.addWidget(QtWidgets.QLabel("⏰ Duración:"))
        self.duration = QtWidgets.QSpinBox()
        self.duration.setSuffix(" minutos")
        self.duration.setRange(1, 180)
        self.duration.setValue(10)
        duration_layout.addWidget(self.duration)
        right_layout.addLayout(duration_layout)

        # Intervalo
        interval_layout = QtWidgets.QHBoxLayout()
        interval_layout.addWidget(QtWidgets.QLabel("🔄 Intervalo:"))
        self.interval = QtWidgets.QSpinBox()
        self.interval.setSuffix(" segundos")
        self.interval.setRange(1, 60)
        self.interval.setValue(5)
        interval_layout.addWidget(self.interval)
        right_layout.addLayout(interval_layout)

        # Botones principales
        self.btn_start = QtWidgets.QPushButton("▶️ INICIAR MEDICIÓN")
        self.btn_start.clicked.connect(self.start_measurement)
        right_layout.addWidget(self.btn_start)

        self.btn_stop = QtWidgets.QPushButton("⏸️ DETENER MEDICIÓN")
        self.btn_stop.clicked.connect(self.stop_measurement)
        self.btn_stop.setEnabled(False)
        self.btn_stop.setStyleSheet("background: #FF9800;")
        right_layout.addWidget(self.btn_stop)

        self.btn_export = QtWidgets.QPushButton("📊 EXPORTAR A EXCEL")
        self.btn_export.setEnabled(False)
        self.btn_export.clicked.connect(self.export_excel)
        self.btn_export.setStyleSheet("background: #4CAF50;")
        right_layout.addWidget(self.btn_export)

        btn_reset = QtWidgets.QPushButton("🔄 REINICIAR TODO")
        btn_reset.clicked.connect(self.reset_all)
        btn_reset.setStyleSheet("background: #9C27B0;")
        right_layout.addWidget(btn_reset)

        btn_refresh = QtWidgets.QPushButton("🔁 ACTUALIZAR PUERTOS")
        btn_refresh.clicked.connect(self.refresh_ports_list)
        btn_refresh.setStyleSheet("background: #2196F3;")
        right_layout.addWidget(btn_refresh)

        # Estado
        self.status = QtWidgets.QLabel("🟦 Seleccione modo y configuraciones")
        self.status.setAlignment(QtCore.Qt.AlignCenter)
        self.status.setStyleSheet("""
            QLabel {
                padding: 12px;
                border-radius: 8px;
                background: #E3F2FD;
                border: 2px solid #90CAF9;
                font-size: 13px;
                font-weight: bold;
                color: #0D47A1;
            }
        """)
        right_layout.addWidget(self.status)

        right_layout.addStretch()

        # Mostrar configuración WiFi cuando se selecciona modo WiFi
        right_layout.insertWidget(3, self.wifi_config_frame)
        self.wifi_config_frame.hide()

        # Unir paneles
        main_layout.addLayout(left_panel, 70)
        main_layout.addWidget(right_panel, 30)

    # ===================== MÉTODOS CORREGIDOS =====================
    def mode_changed(self, mode):
        """Manejador del cambio de modo"""
        self.conn_mode = mode
        
        if mode == "WiFi":
            # Mostrar configuración WiFi y ocultar configuración Serial
            self.wifi_config_frame.show()
            self.port_box.setEnabled(False)
            self.btn_wifi.setEnabled(False)
            self.status.setText("🌐 Modo WiFi: Configure IP y Puerto")
        else:
            # Mostrar configuración Serial y ocultar WiFi
            self.wifi_config_frame.hide()
            self.port_box.setEnabled(True)
            self.btn_wifi.setEnabled(True)
            self.status.setText("🟦 Modo Serial: Seleccione puerto")

    def refresh_ports_list(self):
        """Actualiza lista de puertos"""
        try:
            current = self.port_box.currentText()
            self.port_box.clear()
            
            ports = list(serial.tools.list_ports.comports())
            
            if ports:
                for p in ports:
                    self.port_box.addItem(p.device)
                # Intentar mantener la selección anterior
                if current in [p.device for p in ports]:
                    self.port_box.setCurrentText(current)
                elif ports:
                    self.port_box.setCurrentIndex(0)
            else:
                self.port_box.addItem("Sin puertos disponibles")
                
        except Exception as e:
            print(f"Error actualizando puertos: {e}")
            self.port_box.addItem("Error leyendo puertos")

    def safe_close_serial(self):
        """Cierra conexiones de forma segura"""
        try:
            if self.serial_conn:
                self.serial_conn.close()
        except:
            pass
        self.serial_conn = None
        
        try:
            if self.sock:
                self.sock.close()
        except:
            pass
        self.sock = None

    def configure_wifi(self):
        """Configura WiFi de la ESP32 (solo modo Serial)"""
        port = self.port_box.currentText()
        if not port or "Sin puertos" in port:
            self.status.setText("⚠️ Seleccione un puerto válido")
            return
        
        # Cerrar conexión previa
        self.safe_close_serial()
        
        try:
            self.serial_conn = serial.Serial(port, 115200, timeout=2)
        except Exception as e:
            error_msg = str(e)
            if "denied" in error_msg.lower():
                self.status.setText("🔴 Puerto en uso. Cierre otras apps")
            else:
                self.status.setText(f"🔴 Error: {error_msg[:30]}")
            return

        dialog = WiFiDialog(self)
        if not dialog.exec_():
            self.safe_close_serial()
            return

        ssid, password = dialog.get_data()
        
        try:
            # Limpiar buffer
            if self.serial_conn.in_waiting:
                self.serial_conn.read(self.serial_conn.in_waiting)
            
            self.serial_conn.write(f"SET_WIFI,{ssid},{password}\n".encode())
            
            # Esperar respuesta
            confirmed = False
            for _ in range(40):  # 4 segundos
                if self.serial_conn.in_waiting:
                    line = self.serial_conn.readline().decode(errors="ignore").strip()
                    if "OK_WIFI" in line:
                        confirmed = True
                        break
                QtCore.QThread.msleep(100)
            
            if confirmed:
                self.wifi_configured = True
                self.status.setText("✅ WiFi configurado correctamente")
            else:
                self.status.setText("⚠️ Sin respuesta del ESP32")
                
        except Exception as e:
            self.status.setText(f"🔴 Error: {str(e)[:30]}")
        finally:
            self.safe_close_serial()

    def start_measurement(self):
        if self.measuring:
            return
            
        # Cerrar conexiones previas
        self.safe_close_serial()
        
        try:
            if self.conn_mode == "Serial":
                port = self.port_box.currentText()
                if not port or "Sin puertos" in port:
                    self.status.setText("⚠️ Seleccione un puerto válido")
                    return
                    
                print(f"Conectando a {port}...")
                self.serial_conn = serial.Serial(port, 115200, timeout=2)
                
                # Pequeña pausa para estabilizar
                QtCore.QThread.msleep(1000)
                
            else:  # Modo WiFi - NO requiere configuración previa
                # Obtener IP y puerto de los campos de entrada
                ip = self.wifi_ip_input.text().strip()
                port = int(self.wifi_port_input.text().strip())
                
                if not ip:
                    self.status.setText("⚠️ Ingrese la IP de la ESP32")
                    return
                    
                print(f"Conectando WiFi a {ip}:{port}...")
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.settimeout(3)
                self.sock.connect((ip, port))

            # Iniciar medición
            self.timer.start(self.interval.value() * 1000)
            self.end_timer.start(self.duration.value() * 60000)
            
            self.status.setText(f"🟡 Midiendo ({self.duration.value()} min)")
            self.status.setStyleSheet("""
                QLabel {
                    padding: 12px;
                    border-radius: 8px;
                    background: #FFF3E0;
                    border: 2px solid #FFCC80;
                    font-size: 13px;
                    font-weight: bold;
                    color: #EF6C00;
                }
            """)
            
            self.measuring = True
            self.btn_start.setEnabled(False)
            self.btn_stop.setEnabled(True)
            self.btn_wifi.setEnabled(False)
            
            # Primera lectura
            QtCore.QTimer.singleShot(500, self.read_data)
            
        except Exception as e:
            error_msg = str(e)
            print(f"Error en start_measurement: {error_msg}")
            
            if self.conn_mode == "Serial":
                if "denied" in error_msg.lower():
                    self.status.setText("🔴 Puerto bloqueado. Use 'Reiniciar Todo'")
                elif "not found" in error_msg.lower():
                    self.status.setText("🔴 Puerto no encontrado")
                else:
                    self.status.setText(f"🔴 Error Serial: {error_msg[:30]}")
            else:
                self.status.setText(f"🔴 Error WiFi: {error_msg[:30]}")
            
            self.status.setStyleSheet("""
                QLabel {
                    padding: 12px;
                    border-radius: 8px;
                    background: #FFEBEE;
                    border: 2px solid #EF9A9A;
                    font-size: 13px;
                    font-weight: bold;
                    color: #C62828;
                }
            """)
            
            self.safe_close_serial()
            self.measuring = False
            self.btn_start.setEnabled(True)
            self.btn_stop.setEnabled(False)

    def stop_measurement(self):
        if self.timer.isActive():
            self.timer.stop()
        if self.end_timer.isActive():
            self.end_timer.stop()
            
        self.safe_close_serial()
        
        self.status.setText("🟢 Medición finalizada")
        self.status.setStyleSheet("""
            QLabel {
                padding: 12px;
                border-radius: 8px;
                background: #E8F5E9;
                border: 2px solid #A5D6A7;
                font-size: 13px;
                font-weight: bold;
                color: #2E7D32;
            }
        """)
        
        self.measuring = False
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.btn_wifi.setEnabled(True)
        self.btn_export.setEnabled(True)

    def read_data(self):
        if not self.measuring:
            return
            
        try:
            if self.conn_mode == "Serial" and self.serial_conn:
                # Limpiar buffer de entrada
                if self.serial_conn.in_waiting:
                    self.serial_conn.read(self.serial_conn.in_waiting)
                
                # Enviar comando
                self.serial_conn.write(b"DATA\n")
                self.serial_conn.flush()
                
                # Esperar datos
                QtCore.QThread.msleep(100)
                
                # Leer respuesta
                if self.serial_conn.in_waiting:
                    line = self.serial_conn.readline().decode(errors="ignore").strip()
                    if line:
                        self.process_data(line)
                        
            elif self.conn_mode == "WiFi" and self.sock:
                self.sock.sendall(b"DATA\n")
                line = self.sock.recv(128).decode().strip()
                if line:
                    self.process_data(line)
                    
        except Exception as e:
            print(f"Error en read_data: {e}")

    def process_data(self, line):
        """Procesa los datos recibidos"""
        try:
            parts = line.split(",")
            if len(parts) >= 5:
                uv, nivel, t, h, p = parts[:5]
                
                print(f"Datos recibidos: UV={uv}, Temp={t}, Hum={h}, Pres={p}")
                
                # Actualizar tarjetas
                self.cards["UV"].set_value(f"{uv} ({nivel})" if uv != "NA" else "Sensor no detectado")
                self.cards["Temp"].set_value(f"{t} °C" if t != "NA" else "Sensor no detectado")
                self.cards["Hum"].set_value(f"{h} %" if h != "NA" else "Sensor no detectado")
                self.cards["Pres"].set_value(f"{p} Pa" if p != "NA" else "Sensor no detectado")

                # Guardar datos si son válidos
                if uv != "NA": 
                    self.uv_data.append(float(uv))
                if t != "NA": 
                    self.temp_data.append(float(t))
                if h != "NA": 
                    self.hum_data.append(float(h))
                if p != "NA": 
                    self.pres_data.append(float(p))
                
                self.data_log.append([datetime.now(), uv, nivel, t, h, p])
                
                # Actualizar gráfico cada 5 lecturas
                if len(self.data_log) % 5 == 0:
                    self.update_graph()
                    
        except ValueError as e:
            print(f"Error procesando datos: {e}, línea: {line}")
        except Exception as e:
            print(f"Error inesperado: {e}")

    def update_graph(self):
        """Actualiza el gráfico"""
        try:
            self.ax.clear()
            sel = self.graph_selector.currentText()
            
            colors = {
                "UV": "#FF9800",
                "Temperatura": "#2196F3", 
                "Humedad": "#00BCD4",
                "Presión": "#9C27B0"
            }
            
            if sel == "Índice UV" and self.uv_data:
                self.ax.plot(self.uv_data, color=colors["UV"], linewidth=2, alpha=0.8)
                self.ax.set_title("Índice UV", fontsize=14, fontweight='bold', color=colors["UV"])
            elif sel == "Temperatura" and self.temp_data:
                self.ax.plot(self.temp_data, color=colors["Temperatura"], linewidth=2, alpha=0.8)
                self.ax.set_title("Temperatura (°C)", fontsize=14, fontweight='bold', color=colors["Temperatura"])
            elif sel == "Humedad" and self.hum_data:
                self.ax.plot(self.hum_data, color=colors["Humedad"], linewidth=2, alpha=0.8)
                self.ax.set_title("Humedad (%)", fontsize=14, fontweight='bold', color=colors["Humedad"])
            elif sel == "Presión" and self.pres_data:
                self.ax.plot(self.pres_data, color=colors["Presión"], linewidth=2, alpha=0.8)
                self.ax.set_title("Presión (Pa)", fontsize=14, fontweight='bold', color=colors["Presión"])
            elif sel == "Todas las Variables":
                if self.uv_data: 
                    self.ax.plot(self.uv_data, label="Índice UV", color=colors["UV"], linewidth=1.5)
                if self.temp_data: 
                    self.ax.plot(self.temp_data, label="Temperatura", color=colors["Temperatura"], linewidth=1.5)
                if self.hum_data: 
                    self.ax.plot(self.hum_data, label="Humedad", color=colors["Humedad"], linewidth=1.5)
                if self.pres_data: 
                    self.ax.plot(self.pres_data, label="Presión", color=colors["Presión"], linewidth=1.5)
                
                if any([self.uv_data, self.temp_data, self.hum_data, self.pres_data]):
                    self.ax.legend(fontsize=10)
                    self.ax.set_title("Comparación de Variables", fontsize=14, fontweight='bold', color="#4A148C")
            
            self.ax.grid(True, linestyle='--', alpha=0.4, linewidth=0.5)
            self.ax.set_xlabel("Número de Muestra", fontsize=11)
            self.ax.set_ylabel("Valor", fontsize=11)
            
            self.canvas.draw_idle()
            
        except Exception as e:
            print(f"Error en update_graph: {e}")

    def export_excel(self):
        try:
            path, _ = QtWidgets.QFileDialog.getSaveFileName(
                self, "Exportar Mediciones", 
                f"mediciones_ambientales_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx", 
                "Excel Files (*.xlsx)"
            )
            if path:
                wb = Workbook()
                ws = wb.active
                ws.title = "Mediciones"
                ws.append(["Fecha y Hora", "Índice UV", "Nivel UV", "Temperatura (°C)", "Humedad (%)", "Presión (Pa)"])
                for row in self.data_log:
                    ws.append(row)
                wb.save(path)
                self.status.setText(f"✅ Guardado: {path.split('/')[-1][:25]}")
        except Exception as e:
            self.status.setText(f"🔴 Error al exportar: {str(e)[:30]}")

    def reset_all(self):
        """Reinicio completo"""
        self.stop_measurement()
        
        self.data_log.clear()
        self.uv_data.clear()
        self.temp_data.clear()
        self.hum_data.clear()
        self.pres_data.clear()
        
        for card in self.cards.values():
            card.set_value("Sensor no detectado")
        
        self.ax.clear()
        self.ax.grid(True, linestyle='--', alpha=0.4, linewidth=0.5)
        self.canvas.draw_idle()
        
        self.btn_export.setEnabled(False)
        self.status.setText("🟦 Sistema reiniciado. Listo para nueva medición")
        self.status.setStyleSheet("""
            QLabel {
                padding: 12px;
                border-radius: 8px;
                background: #E3F2FD;
                border: 2px solid #90CAF9;
                font-size: 13px;
                font-weight: bold;
                color: #0D47A1;
            }
        """)
        
        QtCore.QTimer.singleShot(300, self.refresh_ports_list)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle('Fusion')
    
    win = EstacionApp()
    win.show()
    
    sys.exit(app.exec_())