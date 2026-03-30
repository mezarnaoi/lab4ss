import paho.mqtt.client as mqtt
import cv2
import numpy as np
import threading

# Configuration
BROKER = "10.152.215.50"
PORT = 8883
TOPIC_IMAGE = "ssproject/images"
TOPIC_COMMAND = "ssproject/commands"
CA_CERT = "./src/certs/ca.crt"  # path to your CA cert

# Global flags
running = True

# Shared frame storage (thread-safe via lock)
latest_frame = None
frame_lock = threading.Lock()

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT Broker!")
        client.subscribe(TOPIC_IMAGE)
    else:
        print(f"Failed to connect, return code {rc}")

def on_message(client, userdata, msg):
    global latest_frame
    try:
        nparr = np.frombuffer(msg.payload, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is not None:
            with frame_lock:
                latest_frame = img
        else:
            print("Failed to decode image")
    except Exception as e:
        print(f"Error processing image: {e}")

def main():
    global running, latest_frame
    client = mqtt.Client()

    # TLS setup — only CA cert needed since require_certificate false
    client.tls_set(ca_certs=CA_CERT)
    
    client.username_pw_set("esp32cam", "password")

    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(BROKER, PORT, 60)
        client.loop_start()

        print("\n--- ESP32 Camera Controller ---")
        print("Controls:")
        print(" 's' : Take Single Picture")
        print(" 'b' : Begin Stream")
        print(" 'e' : End Stream")
        print(" 'q' : Quit")
        print("-------------------------------\n")

        cv2.namedWindow("ESP32-CAM Stream", cv2.WINDOW_AUTOSIZE)

        while running:
            with frame_lock:
                frame = latest_frame

            if frame is not None:
                cv2.imshow("ESP32-CAM Stream", frame)

            key = cv2.waitKey(30) & 0xFF

            if key == ord('q'):
                running = False
            elif key == ord('s'):
                print("Command: Capture")
                client.publish(TOPIC_COMMAND, "CAPTURE")
            elif key == ord('b'):
                print("Command: Start Stream")
                client.publish(TOPIC_COMMAND, "START-LIVE")
            elif key == ord('e'):
                print("Command: Stop Stream")
                client.publish(TOPIC_COMMAND, "STOP-LIVE")

    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        client.loop_stop()
        client.disconnect()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
