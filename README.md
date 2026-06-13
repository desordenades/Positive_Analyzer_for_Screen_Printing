# Screen Printing Film Analyzer

Automated computer vision tool for screen printing workshops. This script analyzes PDF films to ensure 100% opacity and verifies structural line thicknesses for **43T (110T US)** and **55T (140T US)** screen meshes before exposure.

It has been tested in a real workshop and adjusted with real designs. We work entirely with **water-based inks** and print **manually**, which requires strict tolerances for line thickness to prevent the emulsion from washing out during screen exposure.

## Features
* **Opacity Verification:** Applies a hard threshold to convert any gray or colored pixels into 100% solid black, avoiding UV light leaks during exposure.
* **Dual-Pass Thickness Analysis:** Evaluates the design using a Euclidean distance transform. It checks if solid lines meet the 0.4 mm minimum requirement (for 43T mesh) and if halftone dots meet the 0.35 mm minimum requirement (for 55T mesh).
* **Smart Categorization:** Automatically differentiates between solid spot-color designs and halftone designs by analyzing the number of disconnected error clusters.
* **Visual Output:** Generates a 300 DPI TIFF file overlaying the structural errors in pure red over the original design, allowing the designer to fix the specific lines in Photoshop.
* **Automated Reporting:** Generates a `.txt` summary of all analyzed files and sends an automatic email notification via SMTP.

## Prerequisites

You need Python installed on your system. To install the required libraries, run:

```bash
pip install -r requirements.txt

Setup and Usage
Place your exported PDF films in the same directory as the script.

Note: Export your PDFs from Photoshop/Illustrator at 300 DPI, without downsampling, and using ZIP compression (not JPEG) to preserve edge fidelity.

Open your terminal, navigate to the folder, and run the script:

python analitzador_fotolits.py

The script will output a _ANALYZED.tif file for each PDF and a film_analysis_summary.txt report.

Email Configuration (Optional)
The script includes an automated email notification system. If you want to use it locally without modifying the code, set up the following environment variables in your terminal before running the script:

macOS / Linux:

export SERIGRAFIA_EMAIL_USER="your_email@gmail.com"
export SERIGRAFIA_EMAIL_PASS="your_app_password"
export SERIGRAFIA_EMAIL_TO="recipient_email@gmail.com"

Windows (Command Prompt):

set SERIGRAFIA_EMAIL_USER="your_email@gmail.com"
set SERIGRAFIA_EMAIL_PASS="your_app_password"
set SERIGRAFIA_EMAIL_TO="recipient_email@gmail.com"

Note: If you leave these variables empty, the script will still analyze the films and generate the TIFFs, but it will safely skip the email step.

Contributing
This code was written to solve a real daily issue in our workshop. The script was generated with the assistance of Gemini 3.5 and is structured to be readable and usable by people with basic coding knowledge. Feel free to fork, propose improvements, or adapt the mesh tolerances to your own workshop standards (e.g., plastisol inks or automatic presses).

Author
Gerard (desordenades) / Trama Serigrafia