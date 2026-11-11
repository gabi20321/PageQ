import os
import sys
import time
import cv2
from document_dec import process_frame
from hardlinker import ESP32Controller

def main():
    #cream folderul pentru salvari locale daca nu exista
    scans_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scans")
    os.makedirs(scans_dir, exist_ok=True)

    port = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("PAGEQ_PORT", "COM3")
    esp32 = ESP32Controller(port=port)
    esp32.connect()

    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    #pastram ultima scanare clara timp de cateva cadre ca tasta s sa nu rateze
    last_good_scan = None
    last_good_time = 0.0

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Eroare la citirea camerei!")
                break

            display_frame, status, scanned_doc = process_frame(frame)
            esp32.send_status(status)

            if scanned_doc is not None and status in ("G", "Y"):
                last_good_scan = scanned_doc.copy()
                last_good_time = time.time()

            cv2.imshow("PageQ", display_frame)

            preview = scanned_doc if scanned_doc is not None else last_good_scan
            if preview is not None:
                cv2.imshow("Previzualizare Scanare", preview)

            key = cv2.waitKey(1) & 0xFF
            if key in (ord('s'), ord('S')):
                #permite salvarea daca e verde acum sau a fost verde in ultima secunda
                doc_to_save = scanned_doc if (scanned_doc is not None and status in ("G", "Y")) else (
                    last_good_scan if (last_good_scan is not None and time.time() - last_good_time <= 1.2) else None
                )
                if doc_to_save is not None:
                    ts = time.strftime("%Y%m%d_%H%M%S")
                    ms = int((time.time() % 1) * 1000)
                    filename = os.path.join(scans_dir, f"scan_{ts}_{ms:03d}.jpg")
                    if cv2.imwrite(filename, doc_to_save):
                        print(f"Document salvat cu succes: {filename}")
                else:
                    print("Foaia nu este inca suficient de clara pentru salvare.")
            elif key in (ord('q'), ord('Q')):
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()
        esp32.close()

if __name__ == "__main__":
    main()