# DVR Merge

[FPV (First-person view)](https://en.wikipedia.org/wiki/First-person_view_(radio_control)) is a method used to control a radio-controlled vehicle from the driver or pilot's view point.
Many FPV goggles come with Digital Video Recorders (DVR) built in. These (especially the budget options) usually save the video feed to a file every 3-10 minutes.

While that serves to prevent data corruption, you end up with your flights split up in several files.

This python script uses Tesseract OCR and OpenCV to automatically find matching clips by analyzing their last & first frames. It is also able to automatically merge these videos using ffmpeg.
