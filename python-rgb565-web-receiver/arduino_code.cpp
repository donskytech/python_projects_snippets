#include "esp_camera.h"
#include <WiFi.h>
#include <WiFiUdp.h>
#include <algorithm> 

// --- Network Configuration ---
const char *ssid = "donskytech";
const char *password = "Donsky982!";

// CRITICAL: PC IP and Port (Must match Python config)
const IPAddress receiverIP(192, 168, 1, 3);
const unsigned int receiverPort = 5000;

WiFiUDP udp;

// --- Frame Configuration (QQVGA RGB565) ---
#define FRAME_WIDTH 160
#define FRAME_HEIGHT 120
#define CHUNK_SIZE 1024 // Payload size per UDP packet
#define HEADER_SIZE 10
#define PACKET_SIZE (CHUNK_SIZE + HEADER_SIZE)

// Structure for the 10-byte header 
struct Header {
    uint16_t packet_id;      // Frame Counter (H, 2 bytes)
    uint32_t total_len;      // Total Frame Size (I, 4 bytes) - Should be 38400
    uint32_t start_offset;   // Byte Offset in the frame (I, 4 bytes)
} __attribute__((packed));

// Global frame counter
uint16_t frame_count = 0;

camera_config_t config;

// --- Camera Setup Function ---
void setup_camera() {
    config.ledc_channel = LEDC_CHANNEL_0;
    config.ledc_timer = LEDC_TIMER_0;

    // *** STANDARD AI-THINKER PINOUT ***
    config.pin_d0 = 5;
    config.pin_d1 = 18;
    config.pin_d2 = 19;
    config.pin_d3 = 21;
    config.pin_d4 = 36;
    config.pin_d5 = 39;
    config.pin_d6 = 34;
    config.pin_d7 = 35;
    config.pin_xclk = 0;
    config.pin_pclk = 22;
    config.pin_vsync = 25;
    config.pin_href = 23;
    config.pin_sscb_sda = 26;
    config.pin_sscb_scl = 27;
    config.pin_pwdn = 32;
    config.pin_reset = -1;

    config.xclk_freq_hz = 20000000;
    config.pixel_format = PIXFORMAT_RGB565;
    config.frame_size = FRAMESIZE_QQVGA;
    config.jpeg_quality = 10;
    config.fb_count = 1;

    // Camera init
    esp_err_t err = esp_camera_init(&config);
    if (err != ESP_OK) {
        Serial.printf("Camera init failed with error 0x%x\n", err);
        Serial.println("Check camera module and power supply.");
        while (1) { delay(100); }
    }

    sensor_t *s = esp_camera_sensor_get();
    
    // GC2145 EXPOSURE/GAIN SETTINGS (Kept for stable capture)
    s->set_gainceiling(s, GAINCEILING_8X); 
    s->set_brightness(s, 2);             
    s->set_exposure_ctrl(s, 1);           
    s->set_awb_gain(s, 1);                

    s->set_vflip(s, 1);
    s->set_saturation(s, 0); 
}

void setup() {
    Serial.begin(115200);
    
    // Connect to Wi-Fi
    WiFi.begin(ssid, password);
    Serial.print("Connecting to WiFi...");
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.println("\nWiFi connected.");
    Serial.print("ESP32 IP address: ");
    Serial.println(WiFi.localIP());

    setup_camera();
    udp.begin(receiverPort);
}

void loop() {
    camera_fb_t *fb = esp_camera_fb_get();
    if (!fb || fb->len != (FRAME_WIDTH * FRAME_HEIGHT * 2)) {
        // Serial output for error kept
        if(fb) esp_camera_fb_return(fb);
        return;
    }

    // --- Prepare for Fragmentation ---
    frame_count++;
    size_t total_len = fb->len;
    size_t start_offset = 0;
    uint8_t *data_ptr = fb->buf;

    // --- Fragment and Send ---
    while (start_offset < total_len) {
        size_t send_len = std::min((size_t)CHUNK_SIZE, total_len - start_offset);

        // 1. Create the Header
        Header current_header = {
            .packet_id = frame_count,
            .total_len = (uint32_t)total_len,
            .start_offset = (uint32_t)start_offset
        };

        // 2. Begin UDP Packet
        udp.beginPacket(receiverIP, receiverPort);

        // 3. Write Header (10 bytes)
        udp.write((uint8_t *)&current_header, HEADER_SIZE);

        // 4. Write Payload (up to 1024 bytes)
        udp.write(data_ptr + start_offset, send_len);

        // 5. Send Packet
        udp.endPacket();

        start_offset += send_len;
    }

    esp_camera_fb_return(fb);

    // CRITICAL: Reduce delay to 0ms for max speed
    delay(0); 
}