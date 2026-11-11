import os
import serial
import time

class ESP32Controller:
    def __init__(self, port=None, baudrate=115200):
        self.port = port or os.environ.get("PAGEQ_PORT", "COM3")
        self.baudrate = baudrate
        self.conn = None
        self.last_status = None
        self.last_send_time = 0.0
        self.last_reconnect_try = 0.0

    def connect(self):
        try:
            self.conn = serial.Serial(self.port, self.baudrate, timeout=0.1, write_timeout=0.2)
            time.sleep(2) #timp pentru resetarea conexiunii serial
            print(f"Conectat cu succes la ESP32 pe {self.port}")
            self.last_status = None
            self.send_status("R")
            return True
        except Exception as e:
            self.conn = None
            print(f"Avertisment: Nu m-am putut conecta pe {self.port}. Eroare: {e}")
            return False

    def send_status(self, status):
        now = time.time()
        #reconectare automata la fiecare 3 secunde daca s-a deconectat cablul
        if self.conn is None or not self.conn.is_open:
            if now - self.last_reconnect_try > 3.0:
                self.last_reconnect_try = now
                try:
                    self.conn = serial.Serial(self.port, self.baudrate, timeout=0.1, write_timeout=0.2)
                    self.last_status = None
                except Exception:
                    self.conn = None
                    return
            else:
                return

        #trimite la schimbare sau retrimite periodic la 1.5s pentru sincronizare
        if status != self.last_status or (now - self.last_send_time) > 1.5:
            try:
                mesaj = f"CLS:{status}\n"
                self.conn.write(mesaj.encode("utf-8"))
                self.last_status = status
                self.last_send_time = now
            except Exception:
                try:
                    self.conn.close()
                except Exception:
                    pass
                self.conn = None
                self.last_status = None

    def close(self):
        if self.conn and self.conn.is_open:
            try:
                self.conn.write(b"CLS:R\n")
                self.conn.flush()
                time.sleep(0.05)
                self.conn.close()
            except Exception:
                pass
            print("Conexiune inchisa.")