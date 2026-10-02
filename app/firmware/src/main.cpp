#include <Arduino.h>
#include <Preferences.h>
#include <WiFi.h>
#include <WebServer.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include "lgfx_config.hpp"
PheonixDisplay screen;
Preferences prefs;
WebServer setupServer(80);
JsonDocument state;
String host, errorText;
bool configuring=false, online=false;
unsigned long lastPoll=0;
int candidate=0;
struct Button {int x,y,w,h; String label,action;};
Button buttons[6];int count=0;
void textAt(int x,int y,String s,int size=1){screen.setTextSize(size);screen.setCursor(x,y);screen.print(s);}
void button(int x,int y,int w,String label,String action){buttons[count++]={x,y,w,42,label,action};screen.fillRect(x,y,w,42,TFT_BLACK);screen.setTextColor(TFT_WHITE,TFT_BLACK);textAt(x+8,y+15,label);screen.setTextColor(TFT_BLACK,TFT_WHITE);}
void page(){
 screen.fillScreen(TFT_WHITE);screen.setTextColor(TFT_BLACK,TFT_WHITE);count=0;
 textAt(10,10,"AURACAM",2);
 if(!online){textAt(10,45,"Pi connection unavailable");textAt(10,65,host);textAt(10,90,errorText.substring(0,48));button(8,190,145,"RETRY","retry");button(167,190,145,"WI-FI SETUP","setup");return;}
 String stage=state["stage"]|"idle";textAt(180,14,stage);
 String msg=state["message"]|"";for(int i=0;i<3;i++)textAt(10,42+i*13,msg.substring(i*48,(i+1)*48));
 if(state["busy"]|false){int n=state["remaining"]|0;textAt(12,112,n>0?String(n):"WORKING...",3);return;}
 if(stage=="choose"){
  JsonArray choices=state["candidates"].as<JsonArray>();if(choices.size()==0)return;candidate%=choices.size();auto c=choices[candidate];
  textAt(12,96,String(candidate+1)+" / "+String(choices.size())+"    "+String(c["center_hz"].as<double>()/1e6,2)+" MHz",2);
  textAt(12,124,"Variation: "+String(c["variation_db"].as<float>(),3)+" dB");
  button(8,145,145,"NEXT BAND","next");button(167,145,145,"LOCK FREQUENCY","tune");
 }else if(stage=="ready"||stage=="baseline_review"){
  button(8,145,145,"RESCAN BASELINE","baseline");if(stage=="baseline_review")button(167,145,145,"LOCK BASELINE","lock");
 }else if(stage=="locked"||stage=="gallery"){
  textAt(12,96,"IMAGES: "+String(state["gallery"].size())+" saved on Pi");
  button(8,145,145,"TAKE PHOTO","capture");button(167,145,145,"NEW BASELINE","baseline");
 }
 button(8,192,145,"NEW SESSION","confirm");button(167,192,145,"WI-FI SETUP","setup");
}
void poll(){
 HTTPClient http;http.setConnectTimeout(1500);http.setTimeout(2000);http.begin("http://"+host+"/api/state");int code=http.GET();
 if(code==200){JsonDocument next;auto err=deserializeJson(next,http.getString());online=!err;if(online)state=next;else errorText="Invalid server response";}else{online=false;errorText="Check Pi server and Wi-Fi";}
 http.end();lastPoll=millis();page();
}
void configure(){
 configuring=true;WiFi.disconnect();WiFi.mode(WIFI_AP);
 String password="aura"+String((uint32_t)esp_random(),HEX);WiFi.softAP("AuraCam-Setup",password.c_str());
 screen.fillScreen(TFT_WHITE);screen.setTextColor(TFT_BLACK,TFT_WHITE);count=0;
 textAt(10,12,"CONNECT WI-FI",2);textAt(10,52,"On your phone or Mac, join:");textAt(10,76,"AuraCam-Setup",2);textAt(10,110,"Password: "+password);textAt(10,145,"Then open http://192.168.4.1");textAt(10,175,"Enter your 2.4 GHz Wi-Fi and Pi address.");
 setupServer.on("/",HTTP_GET,[]{setupServer.send(200,"text/html","<meta name='viewport' content='width=device-width,initial-scale=1'><h1>AuraCam setup</h1><form method='post' action='/save'><p>Wi-Fi name <input name='ssid' required></p><p>Password <input name='pass' type='password'></p><p>Pi address <input name='host' value='radiopi.local:8080' required></p><button>Save and connect</button></form>");});
 setupServer.on("/save",HTTP_POST,[]{String h=setupServer.arg("host");h.trim();if(h.indexOf('/')>=0||h.length()>100||setupServer.arg("ssid").isEmpty()){setupServer.send(400,"text/plain","Use hostname:port, e.g. radiopi.local:8080");return;}prefs.putString("ssid",setupServer.arg("ssid"));prefs.putString("pass",setupServer.arg("pass"));prefs.putString("host",h);setupServer.send(200,"text/plain","Saved. Reconnecting; rejoin your normal Wi-Fi.");delay(700);ESP.restart();});setupServer.begin();
}
void action(String a){
 if(a=="setup"){configure();return;}if(a=="retry"){poll();return;}
 if(a=="next"){candidate++;page();return;}
 if(a=="confirm"){screen.fillScreen(TFT_WHITE);screen.setTextColor(TFT_BLACK,TFT_WHITE);count=0;textAt(10,35,"Start a new session?",2);textAt(10,80,"This replaces the active baseline.");textAt(10,100,"Saved images stay on the Pi.");button(8,180,145,"CANCEL","retry");button(167,180,145,"START SESSION","survey");lastPoll=millis()+60000;return;}
 JsonDocument body;body["action"]=a;if(a=="tune")body["center_hz"]=state["candidates"][candidate]["center_hz"];
 String payload;serializeJson(body,payload);HTTPClient http;http.setConnectTimeout(1500);http.setTimeout(2000);http.begin("http://"+host+"/api/action");http.addHeader("Content-Type","application/json");int code=http.POST(payload);http.end();if(code!=202){online=false;errorText="Action failed. Retry connection.";page();return;}poll();
}
void setup(){
 Serial.begin(115200);screen.init();screen.setRotation(1);screen.setBrightness(160);prefs.begin("auracam",false);
 uint16_t calibration[8];if(prefs.getBytesLength("touch")==sizeof(calibration)){prefs.getBytes("touch",calibration,sizeof(calibration));screen.setTouchCalibrate(calibration);}else{screen.calibrateTouch(calibration,TFT_BLACK,TFT_WHITE,12);prefs.putBytes("touch",calibration,sizeof(calibration));}
 String ssid=prefs.getString("ssid","");host=prefs.getString("host","radiopi.local:8080");if(ssid.isEmpty()){configure();return;}
 screen.fillScreen(TFT_WHITE);screen.setTextColor(TFT_BLACK,TFT_WHITE);textAt(10,100,"Connecting to Wi-Fi...",2);
 WiFi.mode(WIFI_STA);WiFi.begin(ssid.c_str(),prefs.getString("pass","").c_str());unsigned long start=millis();while(WiFi.status()!=WL_CONNECTED&&millis()-start<15000)delay(100);
 if(WiFi.status()!=WL_CONNECTED){configure();return;}poll();
}
void loop(){
 if(configuring){setupServer.handleClient();delay(5);return;}
 static bool pressed=false;uint16_t x,y;if(screen.getTouch(&x,&y)){if(!pressed){for(int i=0;i<count;i++)if(x>=buttons[i].x&&x<buttons[i].x+buttons[i].w&&y>=buttons[i].y&&y<buttons[i].y+buttons[i].h){action(buttons[i].action);break;}}pressed=true;}else pressed=false;
 if((int32_t)(millis()-lastPoll)>2500)poll();delay(15);
}
