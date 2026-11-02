# This is the Minor project for MCA degree
### Install dependencies
```python
pip install insightface onnxruntime opencv-python-headless numpy
pip install ultralytics transformers opencv-python-headless torch pillow
```
### Running
```python
python backend.py -- --p "video.mp4" -ph "face.jpg"
python backend.py -- --p "video.mp4" -ph "face1.jpg" "face2.jpg"
python backend.py -- --p "video.mp4" -q "person wearing black"
```
