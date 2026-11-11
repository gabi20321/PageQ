# PageQ — Smart Document Scanner

Sistem hibrid software-hardware pentru detectarea, procesarea și digitizarea automată a documentelor cu feedback vizual în timp real.

## Funcționalități

- **Computer Vision (OpenCV):** Detecție a documentelor prin combinarea măștilor HSV cu muchii Canny, izolare folosind Convex Hull și aliniere plană prin transformare de perspectivă (4-point transform) direct în format A4.
- **Procesare & Claritate:** Evaluare a focusului calculând varianța Laplacian strict pe regiunea de interes (ROI) decupată și îmbunătățirea contrastului pentru text prin algoritmi CLAHE.
- **Feedback Hardware (ESP32):** Controlul unui indicator fizic (LED-uri R/Y/G) care ghidează utilizatorul (Roșu = blurat/lipsă, Galben = detectat dar neclar, Verde = claritate optimă).
- **Comunicare Serială Resilientă:** Protocol text (`CLS:R`, `CLS:Y`, `CLS:G`) la 115200 baud cu mecanism de heartbeat (1.5s), citiri non-blocante pe microcontroler și reconectare automată la pierderea USB-ului.
- **Captură & UI:** Ferestre live (stream original și previzualizare decupată) și mecanism de captură pe taste cu buffer temporal pentru a preveni rateurile la fluctuații scurte de claritate.
