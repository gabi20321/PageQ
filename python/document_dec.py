import cv2
import numpy as np
from collections import deque

def get_blur_score(image):
    #calc claritatea imaginii
    if image is None or image.size == 0:
        return 0.0
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
    h, w = gray.shape[:2]
    #ignora marginile de 10% ca sa nu influenteze rama foii
    roi = gray[int(h * 0.1):int(h * 0.9), int(w * 0.1):int(w * 0.9)]
    if roi.size == 0:
        roi = gray
    return float(cv2.Laplacian(roi, cv2.CV_64F).var())

def order_points(pts):
    #ordonarea de la stanga->dreapta sus->jos
    pts = np.array(pts, dtype="float32")
    y_sorted = pts[np.argsort(pts[:, 1]), :]
    top = y_sorted[:2, :]
    bottom = y_sorted[2:, :]
    tl, tr = top[np.argsort(top[:, 0]), :]
    bl, br = bottom[np.argsort(bottom[:, 0]), :]
    return np.array([tl, tr, br, bl], dtype="float32")

def four_point_transform(image, pts):
    #decupare si indreptarea partiala a unei foi pentru a parea scanata plat
    rect = order_points(pts)
    (tl, tr, br, bl) = rect

    widthA = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
    widthB = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
    maxWidth = max(int(widthA), int(widthB), 1)

    heightA = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
    heightB = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
    maxHeight = max(int(heightA), int(heightB), 1)

    dst = np.array([
        [0, 0],
        [maxWidth - 1, 0],
        [maxWidth - 1, maxHeight - 1],
        [0, maxHeight - 1]], dtype="float32")

    M = cv2.getPerspectiveTransform(rect, dst)
    warped = cv2.warpPerspective(image, M, (maxWidth, maxHeight))
    if maxWidth > maxHeight * 1.15:
        warped = cv2.rotate(warped, cv2.ROTATE_90_CLOCKWISE)
    return cv2.resize(warped, (700, 990), interpolation=cv2.INTER_CUBIC)

def enhance_scan(image):
    #contrast local si accentuare pentru o scanare mai clara
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    #egalizam iluminarea: impartim la fundalul estimat ca sa dispara umbrele si gradientul de lumina
    bg = cv2.GaussianBlur(cv2.morphologyEx(l, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (31, 31))), (0, 0), 25)
    l = cv2.divide(l, bg, scale=235)
    l = cv2.createCLAHE(clipLimit=1.2, tileGridSize=(8, 8)).apply(l)
    #culori mai putin murdare pe hartie
    a = cv2.addWeighted(a, 0.6, np.full_like(a, 128), 0.4, 0)
    b = cv2.addWeighted(b, 0.6, np.full_like(b, 128), 0.4, 0)
    image = cv2.cvtColor(cv2.merge((l, a, b)), cv2.COLOR_LAB2BGR)
    blurred = cv2.GaussianBlur(image, (0, 0), 1.6)
    return cv2.addWeighted(image, 1.5, blurred, -0.5, 0)

def process_frame(frame):
    #proceseaza videoului
    if not hasattr(process_frame, "state"):
        process_frame.state = {
            "blur_history": deque(maxlen=3),
            "prev_pts": None,
            "lost_frames": 0,
            "last_status": "R"
        }
    st = process_frame.state
    original = frame.copy()
    h_frame, w_frame = frame.shape[:2]
    frame_area = h_frame * w_frame

    #masca pentru hartie: luminos si cu saturatie mica, restul fundalului si mana sunt ignorate
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, (0, 0, 150), (180, 65, 255))

    #taiem cu muchiile canny ca sa separam foaia de peretele alb din spate
    gray_full = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(cv2.GaussianBlur(gray_full, (5, 5), 0), 40, 120)
    edges_dilated = cv2.dilate(edges, cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3)), iterations=1)
    mask_split = cv2.bitwise_and(mask, cv2.bitwise_not(edges_dilated))

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    mask_clean = cv2.morphologyEx(mask_split, cv2.MORPH_OPEN, kernel)
    mask_clean = cv2.morphologyEx(mask_clean, cv2.MORPH_CLOSE, kernel)

    contours, _ = cv2.findContours(mask_clean, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:8]

    pts = None
    best_score = -1.0
    cx_frame, cy_frame = w_frame / 2.0, h_frame / 2.0
    max_dist = np.hypot(cx_frame, cy_frame)

    for c in contours:
        area = cv2.contourArea(c)
        #prea mic sau prea mare (perete, cadru intreg) nu e foaie
        if area < 8000 or area > 0.85 * frame_area:
            continue

        #infasuratoarea acopera degetele care tin foaia
        hull = cv2.convexHull(c)
        rect_min = cv2.minAreaRect(hull)
        (rcx, rcy), (rw, rh), _ = rect_min
        if rw == 0 or rh == 0:
            continue

        #forma trebuie sa fie dreptunghiulara si cu proportii de foaie
        rectangularity = cv2.contourArea(hull) / (rw * rh)
        aspect = max(rw, rh) / min(rw, rh)
        if rectangularity < 0.72 or aspect > 2.1 or aspect < 1.1:
            continue

        #penalizare daca atinge marginile cadrului (perete sau monitor in fundal)
        x, y, bw, bh = cv2.boundingRect(hull)
        touches_border = (x <= 4) or (y <= 4) or (x + bw >= w_frame - 4) or (y + bh >= h_frame - 4)
        border_factor = 0.45 if touches_border else 1.0

        #prioritate pentru zona din centrul cadrului si forma dreptunghiulara
        dist_center = np.hypot(rcx - cx_frame, rcy - cy_frame) / max_dist
        center_weight = max(0.2, 1.0 - 0.75 * dist_center)
        cand_score = (area / frame_area) * rectangularity * center_weight * border_factor

        if cand_score > best_score:
            best_score = cand_score
            peri = cv2.arcLength(hull, True)
            approx = cv2.approxPolyDP(hull, 0.035 * peri, True)
            if len(approx) != 4:
                approx = cv2.boxPoints(rect_min).astype(np.int32).reshape(4, 1, 2)
            pts = order_points(approx.reshape(4, 2).astype("float32"))

    #netezire colturi ca sa nu tremure conturul, si tinere cateva cadre daca foaia se pierde scurt
    if pts is not None:
        st["lost_frames"] = 0
        if st["prev_pts"] is not None and np.mean(np.linalg.norm(pts - st["prev_pts"], axis=1)) < 45:
            pts = 0.7 * st["prev_pts"] + 0.3 * pts
        st["prev_pts"] = pts
    elif st["prev_pts"] is not None and st["lost_frames"] < 5:
        st["lost_frames"] += 1
        pts = st["prev_pts"]
    else:
        st["prev_pts"] = None
        st["blur_history"].clear()

    status = "R" #implicit rosu
    scanned_image = None
    blur_score = 0.0

    if pts is not None:
        warped_raw = four_point_transform(frame, pts)
        #media ultimelor cadre ca scorul sa nu sara de la un cadru la altul
        st["blur_history"].append(get_blur_score(warped_raw))
        blur_score = sum(st["blur_history"]) / len(st["blur_history"])

        if blur_score < 12:
            status = "R"
            culoare = (0, 0, 255)
            cv2.putText(original, "BLURAT - Misca mai incet", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, culoare, 2)
        else:
            #prag mai jos cand e deja verde ca sa nu palpaie intre verde si galben
            prag = 25 if st["last_status"] == "G" else 35
            if blur_score > prag:
                status = "G" # verde clar
                culoare = (0, 255, 0)
                cv2.putText(original, "PERFECT - Scanare gata", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, culoare, 2)
                scanned_image = enhance_scan(warped_raw)
            else:
                status = "Y" # galben trebuie tinut pt focus
                scanned_image = enhance_scan(warped_raw)
                culoare = (0, 255, 255)
                cv2.putText(original, "APROAPE - Tine nemiscat", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, culoare, 2)

        cv2.drawContours(original, [pts.astype(np.int32).reshape(4, 1, 2)], -1, culoare, 3)
    else:
        cv2.putText(original, "CAUTARE FOAIE...", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

    st["last_status"] = status
    cv2.putText(original, f"Claritate: {int(blur_score)}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    return original, status, scanned_image