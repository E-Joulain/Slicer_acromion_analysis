# Slicer_acromion_analysis
A 3D Slicer extension for computing acromion radiographic metrics using manually placed fiducial markups. 
The extension provides both numerical output (CSV) and visual overlays to verify measurement accuracy.

# Overview

"acromion_analysis" is designed for the quantitative evaluation of acromion radiographs.
Users manually place anatomical fiducials on an X-ray, and the module computes:

  - scapular axe
  - acromial axe

Visual overlays (lines, angles, arcs) are automatically drawn to confirm that the calculations match anatomical expectations.

# Installation

## Installing 3D Slicer

To use Shoulder-angles-analysis with 3D Slicer, you'll need to download and install 3D Slicer. 
This extension supports the stable and preview versions of 3D Slicer, version 5.3 or higher. For more information on installing 3D Slicer, check out the 3D Slicer Documentation

## Add extension
Download or clone the repository. Unzip the folder where you want on your laptop.
<img width="989" height="449" alt="image" src="https://github.com/user-attachments/assets/6cede515-cde3-4bb8-a80b-27fd6070dd62" />


In 3D Slicer, open Edit → Application Settings → Modules → Additional Module Paths:

<img width="917" height="667" alt="image" src="https://github.com/user-attachments/assets/97d970be-c633-44fb-af2b-8361d4df6609" />

Add the folder "...\Slicer_acromion_analysis\Acromion_analysis" containing the extension and restart Slicer. The path should look like, for example: "C:\Users\Name\Downloads\Slicer_acromion_analysis\Acromion_analysis". 

The module will appear under Custom Modules as Acromion_analysis. 
<img width="1920" height="821" alt="image" src="https://github.com/user-attachments/assets/c0155be5-5e4b-42b1-837c-b51f1ce7fb81" />

# Update the extension 

To update the extension, you just need the download the zip again, replace the new dowloaded folders in the original one. As the path to the extension folder should not have changed, you are ready to go with the last version of the script.

# Workflow

### Step 1 — Load the radiograph

Use the "add DICOM Data" module or drag-and-drop to add all the radiography you would like to analyse.

### Step 2 — Select the volume, side, type of image being analysed

Use the module’s input selector to choose the active X-ray image.

<img width="1349" height="606" alt="image" src="https://github.com/user-attachments/assets/6011af18-a4d3-4803-9f27-806b0dc33846" />

Select the side of the shoudler you are analysing as well as the type. By default, the extension will consider you are working on an anatomical shoudler.
<img width="915" height="571" alt="image" src="https://github.com/user-attachments/assets/00647f6a-e4e6-491a-847b-f6cea28b03df" />

### Step 3 — Place fiducials

Click Place fiducials, a table described the position at which the nodes need to be placed. To see an example image of the nodes's placement and a more precise description, click on "View placement guide (PDF)" which will open a pdf descriptoin. 

The module automatically names the nodes in order and stops when the number needed is reached.

### Step 4 — Compute metrics & save parameters

Click Compute Parameters.

The module:

  - Detects the fiducials

  - Computes the parameters and draws the measurement overlays on the slice view. It saves the values into a CSV file. A widow will open to allow you to choose where you wish to store the results.

# Computed Measurements (will be updated soon)



# Folder structure

Acromion_analysis/

 ├── Acromion_analysis.py    # main python script
 
 ├── Resources/
 
 │   ├── Icons/
 
 │   └── UI/
 
 └── data/                 # Optional exported fiducials
             
