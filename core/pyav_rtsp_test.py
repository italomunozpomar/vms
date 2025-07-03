import av
import cv2

rtsp_url = "rtsp://admin:nunoa2018@192.168.67.63:554/Streaming/Channels/101?tcp/"

container = av.open(rtsp_url)

for frame in container.decode(video=0):
    img = frame.to_ndarray(format="bgr24")
    cv2.imshow("PyAV RTSP", img)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cv2.destroyAllWindows()
