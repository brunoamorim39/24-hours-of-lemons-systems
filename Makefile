# 24 Hours of Lemons — E46 325Ci DRS + PTT Controller
# ESP32 MicroPython firmware

.PHONY: help flash-micropython upload-firmware esp32-monitor esp32-reset deploy clean

# Default serial port (override: make upload-firmware PORT=/dev/ttyXXX)
PORT ?= /dev/cu.usbserial-0001

# Tools (use python3 -m if not on PATH)
ESPTOOL := $(shell which esptool.py 2>/dev/null || echo "python3 -m esptool")
MPREMOTE := $(shell which mpremote 2>/dev/null || echo "python3 -m mpremote")

help:
	@echo "24 Hours of Lemons — E46 325Ci ESP32 Controller"
	@echo ""
	@echo "ESP32 Firmware:"
	@echo "  make flash-micropython FW=<file>  Flash MicroPython to ESP32"
	@echo "  make upload-firmware              Upload firmware/ to ESP32"
	@echo "  make esp32-monitor                Serial monitor (REPL)"
	@echo "  make deploy                       Upload + reset + monitor"
	@echo "  make esp32-reset                  Reset ESP32"
	@echo ""
	@echo "  Override serial port: PORT=/dev/ttyXXX (default: $(PORT))"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean                        Remove __pycache__ etc."

# ============================================================================
# ESP32 Firmware
# ============================================================================

flash-micropython:
	@if [ -z "$(FW)" ]; then \
		echo "Usage: make flash-micropython FW=<micropython.bin> [PORT=$(PORT)]"; \
		echo ""; \
		echo "Download firmware from https://micropython.org/download/ESP32_GENERIC/"; \
		exit 1; \
	fi
	@echo "Flashing MicroPython to ESP32 on $(PORT)..."
	@echo "Hold BOOT button on ESP32 if flash fails to start"
	$(ESPTOOL) --chip esp32 --port $(PORT) erase_flash
	$(ESPTOOL) --chip esp32 --port $(PORT) write_flash -z 0x1000 $(FW)
	@echo "Flash complete. Reset ESP32."

upload-firmware:
	@echo "Uploading firmware/ to ESP32 on $(PORT)..."
	$(MPREMOTE) connect $(PORT) fs mkdir :hw 2>/dev/null; true
	$(MPREMOTE) connect $(PORT) fs cp firmware/config.py :config.py
	$(MPREMOTE) connect $(PORT) fs cp firmware/drs.py :drs.py
	$(MPREMOTE) connect $(PORT) fs cp firmware/ptt.py :ptt.py
	$(MPREMOTE) connect $(PORT) fs cp firmware/main.py :main.py
	$(MPREMOTE) connect $(PORT) fs cp firmware/hw/__init__.py :hw/__init__.py
	$(MPREMOTE) connect $(PORT) fs cp firmware/hw/gpio.py :hw/gpio.py
	$(MPREMOTE) connect $(PORT) fs cp firmware/hw/servo.py :hw/servo.py
	@echo "Upload complete. Reset ESP32 to run."

deploy: upload-firmware
	@echo "Resetting..."
	$(MPREMOTE) connect $(PORT) reset
	@sleep 1
	@echo "Opening serial monitor (Ctrl+] to quit)..."
	$(MPREMOTE) connect $(PORT) repl

esp32-monitor:
	@echo "Opening serial monitor on $(PORT) (Ctrl+] to quit)..."
	$(MPREMOTE) connect $(PORT) repl

esp32-reset:
	@echo "Resetting ESP32 on $(PORT)..."
	$(MPREMOTE) connect $(PORT) reset

# ============================================================================
# Cleanup
# ============================================================================

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "Clean."
