import sdbus
import time
import logging
import subprocess
import os

# --- Configuration ---
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

# --- D-Bus Constants ---
MM_BUS = "org.freedesktop.ModemManager1"
MM_PATH = "/org/freedesktop/ModemManager1"
MM_INTERFACE = "org.freedesktop.ModemManager1"
CALL_INTERFACE = "org.freedesktop.ModemManager1.Call"
MODEM_INTERFACE = "org.freedesktop.ModemManager1.Modem"

# --- ModemManager Call State Enumerations (Simplified) ---
MM_CALL_STATE_INCOMING = 3
MM_CALL_STATE_ACTIVE = 4
MM_CALL_STATE_DISCONNECTED = 7

# --- Global State ---
# Placeholder for the current D-Bus object path of the Modem
modem_path = None
# Placeholder for the D-Bus object path of the active Call
active_call_path = None
# Name of the WAV file to save the audio to
WAV_OUTPUT_FILE = "captured_voice_data.wav"

# --- Audio Recording Placeholder ---
def start_audio_capture(call_path):
    """
    *** CRITICAL: PLACEHOLDER FOR REAL AUDIO CAPTURE LOGIC ***

    Standard ModemManager D-Bus API DOES NOT stream raw audio data.
    The voice audio is routed by the kernel to a system sound device (e.g., ALSA).
    Real-world capture requires external audio libraries or tools (like 'arecord').

    This function simulates starting a capture process.
    """
    logging.info(f"--- [AUDIO CAPTURE STARTED] ---")
    logging.warning(f"Audio from call {call_path} is being routed to an ALSA device.")
    logging.warning(f"You would typically use 'arecord' or a library like 'pyaudio' on the ALSA device.")
    # Example using subprocess (Requires 'alsa-utils' package, e.g., 'sudo apt install alsa-utils')
    # capture_cmd = ['arecord', '-f', 'S16_LE', '-r', '8000', '-c', '1', WAV_OUTPUT_FILE]
    # global audio_process
    # audio_process = subprocess.Popen(capture_cmd)
    # logging.info(f"Simulated command: {' '.join(capture_cmd)}")
    pass

def stop_audio_capture():
    """Simulates stopping the audio capture process."""
    logging.info(f"--- [AUDIO CAPTURE STOPPED] ---")
    # global audio_process
    # if 'audio_process' in globals() and audio_process and audio_process.poll() is None:
    #     audio_process.terminate()
    #     audio_process.wait()
    #     logging.info(f"Audio saved to {WAV_OUTPUT_FILE} (if recording was active).")
    # elif os.path.exists(WAV_OUTPUT_FILE):
    #     logging.info(f"Placeholder: Audio file created at {WAV_OUTPUT_FILE}")
    # else:
    #     logging.info("No audio capture process to stop.")
    pass

# --- D-Bus Call Handlers ---

def handle_call_properties_changed(signal):
    """
    Handles property changes on any Call object (MM signal).
    We check the State property to monitor the call lifecycle.
    """
    global active_call_path

    # Signal arguments: (interface_name, changed_properties, invalidated_properties)
    path = signal.header.path
    changed_properties = signal.body[1]

    if path != active_call_path:
        # Ignore property changes for calls we aren't tracking
        return

    if 'State' in changed_properties:
        state = changed_properties['State']
        logging.info(f"Call {path} state changed to: {state}")

        if state == MM_CALL_STATE_ACTIVE:
            # Call is now active. Start recording.
            start_audio_capture(path)
        elif state == MM_CALL_STATE_DISCONNECTED:
            # Call is over. Stop recording and exit the main loop.
            stop_audio_capture()
            logging.info(f"Call {path} disconnected. Shutting down D-Bus monitor.")
            sdbus.mainloop.stop() # Exit the event loop

def handle_call_added(signal):
    """
    Handles a new Call object being added to the D-Bus, indicating an incoming or outgoing call.
    """
    global active_call_path

    # Signal arguments: (path, properties)
    call_path = signal.body[0]
    properties = signal.body[1]

    state = properties.get('State')
    direction = properties.get('Direction')

    logging.info(f"New Call object added: {call_path}")
    logging.info(f"  State: {state}, Direction: {direction}")

    if state == MM_CALL_STATE_INCOMING:
        logging.info(f"!!! INCOMING CALL DETECTED on {call_path} !!!")
        active_call_path = call_path
        
        try:
            # 1. Answer the call using the Call interface
            call_obj = sdbus.get_proxy(
                MM_BUS, 
                call_path, 
                CALL_INTERFACE,
                # Explicitly specify the object path and interface for safety
                check_path=True,
                check_interface=True
            )
            
            logging.info(f"Attempting to answer call at {call_path}...")
            call_obj.Answer()
            logging.info("Call successfully ANSWERED. Waiting for ACTIVE state...")
            
            # The transition to MM_CALL_STATE_ACTIVE will be caught by handle_call_properties_changed
            
        except sdbus.exceptions.SdBusException as e:
            logging.error(f"Failed to answer call via D-Bus: {e}")
            logging.error("Check Polkit rules for 'org.freedesktop.ModemManager1.Call.Answer' permission!")
        except Exception as e:
            logging.error(f"An unexpected error occurred: {e}")


def find_modem_path(bus):
    """Finds the first available Modem object path."""
    try:
        # Get the ModemManager proxy object
        mm_proxy = sdbus.get_proxy(MM_BUS, MM_PATH, MM_INTERFACE)

        # Call the 'GetManagedObjects' method to find all D-Bus objects exposed by MM
        managed_objects = mm_proxy.GetManagedObjects()

        # Iterate through the objects to find one that supports the Modem interface
        for path, interfaces in managed_objects.items():
            if MODEM_INTERFACE in interfaces:
                logging.info(f"Found Modem at path: {path}")
                return path

    except sdbus.exceptions.SdBusException as e:
        logging.error(f"Could not connect to ModemManager D-Bus: {e}")
        logging.error("Make sure ModemManager is running and D-Bus is accessible.")

    return None

def main():
    """Main function to initialize D-Bus connection and start listening."""
    logging.info("Starting ModemManager Call Answerer...")

    try:
        # 1. Initialize D-Bus connection
        bus = sdbus.open_system()
        
        # 2. Find the Modem Path (required for context, though we listen on MM_PATH)
        global modem_path
        modem_path = find_modem_path(bus)
        if not modem_path:
            logging.error("No active modem found. Exiting.")
            return

        # 3. Set up the signal listeners
        # Listen for the signal that a new call object has been added
        bus.add_signal_handler(
            MM_INTERFACE, # Interface providing the signal
            "CallAdded",  # The signal name
            handle_call_added,
            MM_PATH       # The object path to watch (ModemManager root)
        )

        # Listen for property changes on any object (e.g., call state changing from Incoming to Active)
        # We listen on the root MM path and filter inside the handler for our active call path
        bus.add_signal_handler(
            "org.freedesktop.DBus.Properties",
            "PropertiesChanged",
            handle_call_properties_changed,
            MM_PATH
        )
        
        logging.info("Listening for incoming calls. Press Ctrl+C to stop.")
        
        # 4. Start the D-Bus event loop
        sdbus.mainloop.run()

    except KeyboardInterrupt:
        logging.info("Exiting application by user request.")
    except Exception as e:
        logging.error(f"Fatal error in main loop: {e}")
    finally:
        # 5. Clean up any lingering processes
        stop_audio_capture()
        logging.info("Cleanup complete. Goodbye.")

if __name__ == "__main__":
    main()
