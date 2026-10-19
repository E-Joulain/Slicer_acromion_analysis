cmake_minimum_required(VERSION 3.16.3...3.19.7 FATAL_ERROR)

project(Slicer_acromion_analysis)

#-----------------------------------------------------------------------------
# Extension meta-information
set(EXTENSION_HOMEPAGE "https://www.slicer.org/wiki/Documentation/Nightly/Extensions/Slicer_acromion_analysis")
set(EXTENSION_CONTRIBUTORS "Elise Joulain (UNIGE)")
set(EXTENSION_DESCRIPTION "Point placment extension for acromion study")
set(EXTENSION_ICONURL "https://www.example.com/Slicer/Extensions/Slicer_acromion_analysis.png")
set(EXTENSION_SCREENSHOTURLS "https://www.example.com/Slicer/Extensions/Slicer_acromion_analysis/Screenshots/1.png")
set(EXTENSION_DEPENDS "NA") # Specified as a list or "NA" if no dependencies

#-----------------------------------------------------------------------------
# Extension dependencies
find_package(Slicer REQUIRED)
include(${Slicer_USE_FILE})

#-----------------------------------------------------------------------------
# Extension modules
add_subdirectory(Acromion_analysis)
## NEXT_MODULE

#-----------------------------------------------------------------------------
include(${Slicer_EXTENSION_GENERATE_CONFIG})
include(${Slicer_EXTENSION_CPACK})
