# This is the Minor project for MCA degree
### Install dependencies
```python
pip install insightface onnxruntime opencv-python-headless numpy
pip install ultralytics transformers opencv-python-headless torch pillow
pip install flet flet-video
```
### Running cli
```python
python backend.py -- --p "video.mp4" -ph "face.jpg"
python backend.py -- --p "video.mp4" -ph "face1.jpg" "face2.jpg"
python backend.py -- --p "video.mp4" -q "person wearing black"
```

###Running gui
with dummy
```python
$env:BACKEND="dummy.py"
flet run app.py
```
with real backend
```python
Remove-Item Env:BACKEND
flet run app.py
```

###Testing cut
```python
python models\backend.py -- --p "C:\videos\test.mp4" -q "person wearing black" -o results.json
python models\cut.py --segments results.json -o clips\test
```
