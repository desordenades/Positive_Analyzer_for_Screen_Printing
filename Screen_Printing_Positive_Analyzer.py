"""
Screen Printing Film Analyzer
-------------------------------------------------------
This code was generated with the assistance of Gemini 3.5.

Automated computer vision tool for screen printing workshops. 
It analyzes PDF films to ensure 100% opacity and verifies structural 
line thicknesses for 43T and 55T screen meshes before exposure.
It has been used in a real workshop, with mm and threads per cm in the mesh units.
43T = 110T (threads per inch)
55T = 140T (threads per inch)
It has been tested with real designs that gave us some problems, and it has been adjusted
as we corrected the designs to finally expose the screens and print them. 
We work always with WATERBASED inks and print MANUALLY.

Feel free to contribute. 
Consider that this code was written by a newbie in coding, and the objective is that it can
be used by anyone with very little coding knowledge, that's the reason for so many comments.
"""

import fitz  # PyMuPDF for PDF reading and rasterization
import cv2  # OpenCV for computer vision and pixel matrix operations
import numpy as np  # NumPy for high-speed vectorized mathematical calculations
import os  # OS module to interact with paths and environment variables
from PIL import Image  # Pillow to inject real physical resolution metadata (DPI)

import smtplib  # Native library to manage SMTP network connections
from email.mime.multipart import MIMEMultipart  # MIME container structuring
from email.mime.text import MIMEText  # Text message body management
from email.mime.base import MIMEBase  # Data structure management for attachments
from email import encoders  # Base64 encoder for file transfer

# --- GENERAL TECHNICAL CONFIGURATION ---
DPI = 300  # Standard resolution for homogeneous image processing

# 1. 43T Mesh Parameters (Standard for solid lines and shapes)
thickness_43_mm = 0.4
thickness_px_43 = (thickness_43_mm * DPI) / 25.4
radius_43 = (thickness_px_43 / 2) * 0.85  # 85% tolerance margin to avoid false positives

# 2. 55T Mesh Parameters (Fine detail for halftone dots/lines)
thickness_55_mm = 0.35
thickness_px_55 = (thickness_55_mm * DPI) / 25.4
radius_55 = (thickness_px_55 / 2) * 0.85  # Tolerance margin for high-density resolution

# --- SECURITY: AUTOMATIC CREDENTIALS (GITHUB READY) ---
# To use email notifications on your local machine, set these environment variables.
# If left empty, the script will process files normally but will skip sending the email.
SENDER_EMAIL = os.environ.get("ScreenPrinting_EMAIL_USER", "your_email@gmail.com")
APP_PASSWORD = os.environ.get("ScreenPrinting_EMAIL_PASS", "your_app_password")
RECIPIENT_EMAIL = os.environ.get("ScreenPrinting_EMAIL_TO", "recipient_email@gmail.com")


def process_doc(path_pdf):
    """
    Main computer vision function. Opens the first page of the PDF, rasterizes it
    to the workshop's DPI, and binarizes it using a hard threshold to force 100% opacity.
    Calculates a distance transform to create a 3D topographic map of the thickness.
    """
    doc = fitz.open(path_pdf)
    pix = doc[0].get_pixmap(dpi=DPI, colorspace=fitz.csRGB)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, 3)
    img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

    # Convert to grayscale and apply hard threshold (Any color/gray below 240 becomes black)
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)

    # Calculate the distance of each pixel to the transparent background (structural size)
    dist = cv2.distanceTransform(binary, cv2.DIST_L2, 5)

    def generate_error_mask(radius, thickness_px):
        """
        Internal morphological function. Virtually reconstructs the image by dilating only
        valid structural pixels with an odd-sized kernel (prevents matrix shifting).
        Subtracts the reconstruction from the original to isolate structural errors.
        """
        valid_zones = (dist >= radius).astype(np.uint8) * 255
        kernel_size = int(np.ceil(thickness_px))
        if kernel_size % 2 == 0:
            kernel_size += 1
        kernel = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE, (kernel_size, kernel_size)
        )
        valid_lines = cv2.dilate(valid_zones, kernel)
        return cv2.bitwise_and(binary, cv2.bitwise_not(valid_lines))

    # Generate the two phases of geometric analysis (Dual-Pass)
    errors_43 = generate_error_mask(radius_43, thickness_px_43)
    errors_55 = generate_error_mask(radius_55, thickness_px_55)

    # Connected components analysis for the standard mesh (counting and measuring isolated spots)
    num_labels_43, _, stats_43, _ = cv2.connectedComponentsWithStats(
        errors_43, connectivity=8
    )
    px_error_43 = np.sum(errors_43 > 0)
    max_area_43 = (
        np.max(stats_43[1:, cv2.CC_STAT_AREA]) if num_labels_43 > 1 else 0
    )

    # Calculate absolute pixel loss for the 55T mesh
    px_error_55 = np.sum(errors_55 > 0)

    # Calculate surface ink loss ratios
    total_ink_px = np.sum(binary > 0)
    loss_43 = (
        (px_error_43 / total_ink_px) * 100 if total_ink_px > 0 else 0
    )
    loss_55 = (
        (px_error_55 / total_ink_px) * 100 if total_ink_px > 0 else 0
    )

    # Automatic document type identification (>2500 error clusters defines a Halftone)
    is_halftone = (num_labels_43 - 1 > 2500) and (px_error_43 > 125000)

    status = ""
    visual_mask = None
    critical_px_report = 0

    if is_halftone:
        # Progressive evaluation logic for halftone designs
        if loss_43 <= 5.0:
            status = f"PASS 43T Mesh (Halftone. Loss: {loss_43:.1f}%)"
            visual_mask = errors_43
            critical_px_report = px_error_43
        elif loss_55 <= 5.0:
            status = f"WARNING: 55T Mesh Required (Fine halftone. 55T Loss: {loss_55:.1f}%)"
            visual_mask = errors_55
            critical_px_report = px_error_55
        else:
            status = f"ERROR. Fix design (Halftone unviable for 55T. Loss: {loss_55:.1f}%)"
            visual_mask = errors_55
            critical_px_report = px_error_55
    else:
        # Strict evaluation logic for solid line designs (Forces 43T threshold)
        if max_area_43 <= 250:
            status = f"PASS 43T Mesh (No breaks. Total px: {px_error_43})"
            visual_mask = errors_43
            critical_px_report = px_error_43
        else:
            status = f"ERROR. Fix design (Continuous thin line detected: {max_area_43} px)"
            visual_mask = errors_43
            critical_px_report = px_error_43

    # Visual output reconstruction. White background, pure black design, and errors in pure red [0,0,255]
    clean_gray_base = cv2.bitwise_not(binary)
    visual_result = cv2.cvtColor(clean_gray_base, cv2.COLOR_GRAY2BGR)
    visual_result[visual_mask > 0] = [0, 0, 255]

    doc.close()
    return visual_result, status, critical_px_report


def send_email_report(file_path):
    """
    External automation function. Opens an SMTP connection with the remote server,
    encodes the text report in Base64, and securely sends the notification email.
    """
    # Security check: If the user hasn't set up their credentials, skip the email step cleanly.
    if "your_email@gmail.com" in SENDER_EMAIL or "your_app_password" in APP_PASSWORD:
        print("\n[Notice] Default email detected. Skipping email notification.")
        return

    print("Preparing email delivery...")
    msg = MIMEMultipart()
    msg["From"] = SENDER_EMAIL
    msg["To"] = RECIPIENT_EMAIL
    msg["Subject"] = "Automated Report: Screen Printing Film Analysis"

    body_message = "Hello,\n\nAttached you will find the automatically generated report detailing the status of the currently processed films.\n\nPlease check the generated TIFF files to review the structural errors detected.\n\nBest regards."
    msg.attach(MIMEText(body_message, "plain"))

    try:
        with open(file_path, "rb") as attachment:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(attachment.read())
        encoders.encode_base64(part)
        part.add_header(
            "Content-Disposition", f"attachment; filename= {file_path}"
        )
        msg.attach(part)
    except Exception as e:
        print(f"Error attaching the text file: {e}")
        return

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(SENDER_EMAIL, APP_PASSWORD)
        full_text = msg.as_string()
        server.sendmail(SENDER_EMAIL, RECIPIENT_EMAIL, full_text)
        server.quit()
        print(f"Email sent successfully to {RECIPIENT_EMAIL}.")
    except Exception as e:
        print(f"There was an error with the SMTP connection: {e}")


def run_analyzer():
    """
    Directory orchestration function. Scans the local folder, sends each PDF to the vision engine,
    generates the global summary report, and exports the review files as TIFFs at 300 DPI.
    """
    current_path = "."
    summary_file = "film_analysis_summary.txt"
    processed_files = 0

    with open(summary_file, "w", encoding="utf-8") as report:
        report.write("THICKNESS ANALYSIS REPORT\n")
        report.write("=" * 35 + "\n\n")

        for filename in os.listdir(current_path):
            if (
                filename.lower().endswith(".pdf")
                and "_ANALYZED" not in filename
            ):
                print(f"Analyzing: {filename}...")
                processed_files += 1
                try:
                    img_res, status, px_error = process_doc(filename)

                    base_name = os.path.splitext(filename)[0]
                    output_name = f"{base_name}_ANALYZED.tif"

                    # Convert channel order (BGR to RGB) required by the Pillow library
                    img_res_rgb = cv2.cvtColor(img_res, cv2.COLOR_BGR2RGB)
                    img_pil = Image.fromarray(img_res_rgb)
                    # Force the TIFF metadata header to recognize the true 300 DPI scale
                    img_pil.save(output_name, format="TIFF", dpi=(DPI, DPI))

                    report.write(f"FILE: {filename}\n")
                    report.write(f"STATUS: {status}\n")
                    report.write(f"CRITICAL PX: {px_error}\n")
                    report.write("-" * 20 + "\n")
                except Exception as e:
                    report.write(f"ERROR processing {filename}: {str(e)}\n")
                    print(f"Failed to process {filename}. Error: {e}")

    print(
        f"\nImage processing finished. Analyzed {processed_files} document(s)."
    )

    # Trigger the notification channel if data was processed
    if processed_files > 0:
        send_email_report(summary_file)


if __name__ == "__main__":
    run_analyzer()