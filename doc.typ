#set document(
  title: "SmartCull AI"
)

#set page(
  paper: "a4",
  margin: (top: 1.2in, bottom: 1.2in, left: 1in, right: 1in),

  // Line at the top of every page
  header: line(length: 100%, stroke: 1pt),

  // Line at the bottom, with the page number under it
  footer: [
    #line(length: 100%, stroke: 1pt)
    #v(0.2em)
    #align(center)[#context counter(page).display()]
  ],
)

#set text(
  font: ("Times New Roman"),
  size: 12pt
)

#set par(
  justify: true,
  leading: 1.1em
)

#set heading(numbering: "1.1")

#show heading.where(level: 1): it => {
  set align(center)
  set text(size: 14pt, weight: "bold")
  v(0.5em)
  upper(it)
  v(0.5em)
}

#show heading.where(level: 2): it => {
  set text(size: 12pt, weight: "bold")
  v(0.6em)
  it
  v(0.3em)
}

// ---------------- ABSTRACT ----------------

#heading(numbering: none)[Abstract]

Photographers and videographers capture hundreds or thousands of photos and video clips during events, making the process of reviewing, organizing, and selecting useful media time-consuming and repetitive. Manually identifying sharp, well-exposed, non-repetitive, and relevant photographs and video footage can significantly increase the time required before editing and post-production. This project presents SmartCull AI, an intelligent photo and video culling system designed to automate and assist in the initial media selection process. The system analyzes photographs to evaluate properties such as sharpness, blur, exposure, duplicate and near-duplicate content, face detection, and closed eyes. For video footage, representative frames are extracted and analyzed to evaluate sharpness, exposure, camera stability, unusable frames, duration, and visual similarity between clips.

SmartCull AI also allows users to search for photos based on specific angles, opacity, number of people, specific individuals, and exposure. It provides natural-language media search, allowing users to describe the content they want to find using text prompts. The system compares the query with visual information from photographs and sampled video frames to identify relevant results. For videos, it can further perform video-moment retrieval by identifying the approximate timestamp at which a requested event or scene occurs. The system supports duplicate and near-duplicate detection and can recommend higher-quality media from similar groups. All recommendations are presented for user review, and original files are preserved without automatic deletion. Selected photographs and video clips can be exported into organized folders for further editing and post-production. The project aims to reduce the time spent finding and sorting media and streamline the overall media production process.

#pagebreak()

// ---------------- INTRODUCTION ----------------

= Introduction

Photography and videography are central to events such as weddings, concerts, conferences, and sports. A single event can produce hundreds or even thousands of photographs and video clips. Before any editing can begin, a large share of this material has to be reviewed and filtered, because much of it is blurred, poorly exposed, shaky, or nearly identical to other shots.

== Problem Statement

Reviewing and selecting media by hand is slow, repetitive, and tiring. Photographers must check each image for sharpness and exposure, find shots where subjects blinked, and compare near-duplicates to pick the best one. For video, they have to scrub through long footage to find usable segments or a specific moment. This work adds a lot of time before post-production starts, and fatigue can cause good shots to be overlooked or poor ones to be kept.

Existing tools often handle only part of the problem. Some support basic ratings or sorting, but they do not combine quality assessment, duplicate grouping, people-based filtering, and content-based search in one workflow.

== Existing System

At present, media culling is done mostly by hand. The photographer imports every file into a general-purpose tool such as a file browser, an image viewer, or photo-management software like Adobe Lightroom. They then go through the files one by one, zooming in to check focus, comparing similar frames side by side, and flagging or rating the keepers. Video is reviewed the same way: clips are played back, often at length, to judge stability and find the useful segments.

Some commercial tools add partial automation, such as rating, sorting, or basic grouping of similar shots. Even so, the existing approach has several limitations:

- *Time-consuming:* Every photo and clip has to be reviewed manually, which delays editing and delivery.
- *Inconsistent:* Fatigue and subjective judgment lead to uneven decisions across a large set.
- *Weak duplicate handling:* Near-duplicate shots are hard to spot and compare across hundreds of images.
- *Limited search:* Finding a particular person, scene, or moment usually means scrolling through everything. Text-based search of visual content is rare, and moment-level search inside videos is rarer still.
- *Fragmented workflow:* Quality checks, duplicate grouping, people filtering, and content search are spread across different tools, if they are available at all.
- *Little support for video:* Most culling tools focus on still photographs, so video footage is still reviewed almost entirely by hand.

== Proposed System

The proposed system, *SmartCull AI*, brings these tasks into one assisted workflow. It analyzes photographs and sampled video frames automatically and gives the user ranked recommendations instead of an unsorted pile of files.

Its main features are:

- *Quality analysis:* Sharpness, blur, and exposure are measured for photographs, and camera stability and unusable frames are measured for video.
- *Duplicate detection:* Similar and near-duplicate media are grouped, and the best item in each group is recommended.
- *People analysis:* Faces are detected, closed eyes are flagged, and media can be filtered by number of people or by a specific individual.
- *Natural-language search:* Users describe what they want in plain text, and the system matches the query against photographs and video frames.
- *Video-moment retrieval:* The system estimates the timestamp at which a requested event or scene occurs in a video.
- *Safe, reviewable output:* All suggestions are presented for user review, original files are never deleted automatically, and the selected media is exported into organized folders for editing.

Compared with the existing approach, the proposed system reduces the time spent on repetitive review, applies the same criteria to every file, and makes it easy to find specific people, scenes, and moments. The final selection still rests with the user.

== Objectives

The main objectives of this project are:

+ To automatically assess photographs and video footage for technical quality, including sharpness, exposure, and stability.
+ To detect duplicate and near-duplicate media and recommend the best item from each group.
+ To detect faces and closed eyes, and to support search by number of people and by specific individuals.
+ To provide natural-language search over photographs and videos, including timestamp-level moment retrieval in video.
+ To keep the user in control by presenting recommendations for review and preserving all original files.
+ To export selected media into organized folders and reduce the time spent between capture and editing.

#pagebreak()

= System Requirement Specification

== Software Requirements

#figure(
  table(
    columns: (auto, 1fr),
    align: (left, left),
    inset: 8pt,
    table.header[*Item*][*Requirement*],
    [Operating system], [Windows 10 or 11],
    [Programming language], [Python 3.10 or later],
    [Image and video processing], [OpenCV, ffmpeg],
    [Person and object detection], [YOLO],
    [Text-image matching], [SigLIP (or CLIP)],
    [Face matching], [InsightFace],
    [User interface], [Flet],
    [Caching], [Radis],
    [Packaging], [PyInstaller],
  ),
  caption: [Software requirements],
)

== Hardware Requirements

#figure(
  table(
    columns: (auto, 1fr, 1fr),
    align: (left, left, left),
    inset: 8pt,
    table.header[*Component*][*Minimum*][*Recommended*],
    [Processor], [Dual-core CPU, 2.0 GHz], [Quad-core or better CPU],
    [RAM], [8 GB], [16 GB],
    [Storage], [10 GB free space], [SSD with 50 GB or more free space],
    [GPU], [Not required], [Optional, to speed up model inference],
    [Display], [1366 x 768], [1920 x 1080],
  ),
  caption: [Hardware requirements],
)

#pagebreak()

= Modules

// Module headings are written as "Module 1: ..." so turn off automatic numbers here
#set heading(numbering: none)

The system is divided into 4 modules. Each module performs a specific task and passes its results to the next.

== Module 1: Media Import and Preprocessing

This module is the entry point of the system. The user selects a folder of photographs and videos, and the module scans it, validates the file formats, and builds a list of media items. Corrupted or unsupported files are skipped and reported to the user. For video, the module extracts representative frames at regular intervals, so later modules work on sampled frames instead of every frame.

*Input:* folder of photographs and videos. *Output:* validated media list and sampled video frames.

*Technologies used:* Python for file scanning, OpenCV for reading images and frames, and ffmpeg for decoding video and extracting frames.

== Module 2: Models and Processing

This module does the bulk of the analysis. It takes the photographs and sampled video frames from Module 1 and runs them through several analysis stages:

- *Quality analysis:* Sharpness and blur are estimated using the variance of the Laplacian, and exposure is judged from the brightness (underexposed or overexposed regions). For video, camera stability is measured from frame-to-frame motion, and unusable frames (heavily blurred, black, or washed out) are flagged.
- *Person and face analysis:* YOLO detects people in each image or frame and counts them. InsightFace detects faces, estimates whether the eyes are closed, and produces face embeddings that are used to find a specific individual in videos and photos from a reference photo.
- *Duplicate detection:* Visual embeddings are compared to group similar and near-duplicate media. Within each group, the item with the best quality score is recommended.
- *Semantic search:* SigLIP (or CLIP) converts photographs and sampled frames into embeddings, and converts the user's text query into the same space. Similarity scores rank the results. For video, the score of each sampled frame is mapped back to its timestamp, which gives the approximate moment at which the requested scene occurs.

*Input:* validated media list and sampled frames. *Output:* quality scores, face and person data, duplicate groups, embeddings, and ranked search results with timestamps.

*Technologies used:* OpenCV for quality metrics, YOLO for person detection, InsightFace for face detection and matching, and SigLIP or CLIP for text-image matching. The models can run on the CPU, and a GPU can be used optionally to speed up inference.

== Module 3: Backend Controller (Middleware)

This module acts as middleware between the user interface and the processing modules. It receives requests from the interface (such as "analyze this folder", "search for a query", or "filter by number of people"), passes them to the correct module, and returns the results in a structured form. It also runs long tasks in the background and reports progress, so the interface stays responsive during analysis. Computed scores and embeddings are cached, so repeated searches and filters do not need the media to be analyzed again. The module also combines individual scores into a final recommendation for each item and keeps all outputs read-only with respect to the original files.

*Input:* requests from the user interface and results from Module 2. *Output:* JSON responses with ranked results, recommendations, and progress updates.

*Technologies used:* Python for the controller logic, a command-line and JSON interface for communication with the front end, background worker threads or processes for long-running tasks, and Radis or on-disk files for caching results and embeddings.

== Module 4: User Interface and Export

This module is the front end of the system. It lets the user import media, run analysis, search, filter, preview clips, and review all recommendations. After reviewing, the user selects the items to keep, and the module exports them into organized folders for editing and post-production. It only copies files to the output location, so the original files stay unchanged.

*Input:* user actions and results from the other modules. *Output:* reviewed selection and organized export folders.

*Technologies used:* Flet for the graphical interface, a command-line and JSON interface to communicate with the backend, Python for copying files into organized folders, and PyInstaller for packaging as a standalone executable.

