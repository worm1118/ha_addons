# 수정 내역 (눌러서 확인하세요)

## 10.331

* "serial connection lost!" 발생 시 runtimeError 넘기지 않고 return None으로 변경해 봄. 어떻게 될지 모름.

## 10.33

* 에러 메시지 일부 수정

## 10.32

* 디스코드 웹훅 주소를 설정으로 분리

## 10.31

* fan index 문제로 죽는 현상 방어 코드 추가 (line 1065)
* "serial connection lost!" 에러 발생 시 사용하는 애드온 재시작 함수 (restart_addon()) 및 호출 추가 @메인
* 디스코드 메시지 전달 기능 추가

## 10.3

* entrance\_mode가 minimal일때 엘리베이터 호출 시도하면 죽는 문제 수정

## 10.2

* 10.1 버전에서 실시간 에너지 사용량이 알수 없음으로 유지되는 오류 수정

## 10.1

* 10 버전이 실시간 에너지 사용량 보이는 집에서 켜지지 않는 오류 수정

## 10

* 구성요소 한글이름 추가, object\_id(entity\_id) 별도로 명시
  * **주의**: HA 버전 2023.8 이후 이 애드온을 새로 설정하신 경우 구성요소들의 entity\_id가 light.sds\_wallpad\_sds\_light\_1 형태이셨을 수 있습니다.
  업데이트 후에는 기존 의도대로 light.sds\_light\_1 형태의 구성요소가 생성됩니다. 변경을 원치 않으시는 경우 애드온 설정의 prefix를 sds\_wallpad\_sds 로 변경하시면 유지가 가능합니다.
* **주의**: gas\_valve를 sensor에서 switch로 변경
  * 이제 entrance\_mode를 사용하지 않는 경우에도 가스밸브 차단을 지원합니다.
* 실시간 에너지 사용량의 소수점 자리수를 세팅할 수 있도록 지원
  * 실시간 전력사용량이 100배로 표기되는 경우, 이제 power\_decimal을 2로 설정하시면 해결이 가능합니다.
* 공동현관 문열림 동작 시 통화 2초 유지 후 여는 옵션 추가 (intercom\_delay)
  * 일부 환경에서 공동현관 초인종이 울렸을때 통화를 시작하자마자 문열림을 보내면 무시되는 경우가 있습니다. 해당되실 때 사용하세요.

## 9.8

* PAHO-MQTT 라이브러리 2.0 호환성 대응

## 9.7

* 9.6 버전 오류 수정

## 9.6

* 신형 현관스위치에서 early\_response를 0으로 세팅하면 완전히 꺼질수 있도록 변경
  * 신형 현관스위치(entrance\_mode: new) 사용하던 중 이번 버전에서만 동작이 안되면 early\_response 설정값을 1 올려서 사용하세요.
* discovery 속도 문제로 HA에 초기 상태 등록 안되는 경우 있어서, 일정 시간 지난 후 한번 재등록
* 인터폰 문열림기능 종료 시퀀스 단순화
* MQTT 연결 시 client id 설정

## 9.5

* 일부 환경에서 "s6-overlay-suexec: fatal: can only run as pid 1" 오류 해결

## 9.4

* 소켓 끊어졌을때 애드온 자체적으로 재연결 시도하도록 재수정
  * EW11 사용시 연결이 주기적으로 끊어지는 경우 EW11 설정 페이지의 Communication Settings - Socket Settings - Timeout(s) 이 0으로 설정되어 있는지 확인이 필요합니다.
  * 문제가 있는 경우 [Github issue 페이지](https://github.com/n-andflash/ha_addons/issues) 혹은 [HA 카페](https://cafe.naver.com/koreassistant)에 글을 올려주세요.
* 공동현관 예약 동작 안하는 경우 수정

## 9.3

* water/gas device class 제거 및 유량 단위로 원복

## 9.2

* 수정내역 페이지 형식 수정
* device class에 맞춰서 water/gas 사용량 단위 수정

## 9.1

* 소켓 끊어졌을때 멈춰있는 대신 종료되도록 수정
    * 연결이 불안정한 환경에서는 애드온 "실행 감시" 기능을 켜두세요.
* 조명 패킷 깨졌을때 애드온 죽을수 있는 현상 수정
* 사용량 센서에 device class 적용

## 9

* HA core 2021.3의 변경사항: FAN(환기장치) 의 속도 표시방법 변경
    * 이번 버전부터는 HA core 2021.3 이후 버전이 필요합니다.
    * **제공되는 sds\_fan.yaml 파일을 사용하시던 경우 새로운 파일로 직접 교체가 필요합니다.**
    * **fan.set\_speed 서비스가 fan.set\_preset\_mode 로 변경 되었습니다. 사용하시던 자동화가 있으면 점검이 필요합니다.**

## 8.4

* HA core 2021.2 의 변경사항으로 인한 warning 발생 수정
    * 이번 버전부터는 HA core 2021.2 이후 버전이 필요합니다.

## 8.3

* socket 사용시 exception 발생할 가능성 수정 (github issue #1 대응)

## 8.2

* 현관 초인종이 울린 상태일때 현관 문열림 안되는 현상 수정
* 설치 후 MQTT 주소 변경 안했을때 경고, 주소 앞에 프로토콜(mqtt:// 등) 붙인 경우 무시, 관련 에러메시지 정리
* dump\_time 10초 미만 설정 시 10초로 조정

## 8.1

* Docker base image를 $BUILD\_PROM (alpine) 에서 python:3 로 변경 (라즈베리파이 설치 오류 대응)

## 8

* 현관 문열림 기능 추가
* 현관/공동현관 초인종 울림 여부를 확인하는 binary sensor 추가
* HA에서 조명, 환기장치 제어 시 switch에 상태 선반영

## 7.1

* 애드온 시작할때 로그에 버전번호 출력

## 7

* 디스플레이 형태의 신형 현관스위치가 설치된 가정에서의 엘리베이터 호출 지원
* MQTT 로그인 정보가 잘못되었을 때 에러메시지 출력되도록 변경

## 6

* 실시간에너지 관련 단위 수정 및 예제 추가
* 초인종 울린 후 addon에서 통화하지 않고 종료되었을 때 제대로 마무리되지 않는 현상 수정
* MQTT topic을 retain하는 대신 HA 재시작 메시지 받았을때 전부 재등록하도록 변경
    * HA 113.0 에 추가된 MQTT birth 메시지를 반영하였습니다.
    * 구버전의 HA를 사용하시는 경우 HA를 재시작할 때마다 애드온을 재시작해주셔야 할 수 있습니다.

## 5.5

* socket에서 dump\_mode 사용 가능하도록 수정

## 5.4

* MQTT broker가 재시작했을 때, 재연결되면 다시 subscribe하도록 개선

## 5.3

* intercom\_mode 설정 schema 추가

## 5.2

* 가상 인터폰 오류 수정

## 5.1

* 가상 인터폰이 A4 외에 다른 곳에도 붙을 수 있도록 configuration에 추가

## 5

* **가상 인터폰 등록해서 공동현관 문열림 기능 제공** ("intercom\_mode")
* 모든 entity가 MQTT 통합 구성요소에 "sds\_wallpad" 기기로 등록되도록 추가
* entrance\_mode가 full일 때 일괄소등 기능 제거: 필요 시 아래와 같이 개별 전등을 전부 끄는 서비스로 대체하세요.
```yaml
service: light.turn_off
entity_id:
  - light.sds_light_1
  - light.sds_light_2
  ...
```
* 현관/공동현관 관련 기존 임시 구현 제거
* 환기장치와 공동현관 문열림 관련 automation 샘플 YAML 제공
* Lovelace 구성 예제 제공

## 4.2

* receive 버퍼에 데이터가 쌓여있을 때 명령 여러개 연속으로 보내지 않도록 수정
* (내부 구현 변경) serial과 socket을 같이 가져가는게 점점 지저분해져서 둘을 class로 변경

## 4.1

* B0xx 응답 뒤에도 새로운 명령 보내도록 타이밍을 추가

## 4

* 재시도 한도를 횟수가 아닌 시간으로 변경 (max\_retry 해석 방법만 변경, 설정 수정 필요 없음)
* MQTT disconnect 됐을 때 경고메시지 추가
* README 면책조항 추가

## 3.4

* 공동현관 문열림 테스트하기 위한 doorbell\_mode 준비 (비활성화 되어있음)
* configuration에 빠진 항목 있을때 로그가 중복 출력되는 현상 수정
* dump\_time 켤때 오류 수정
* 패킷 분석 내용 공유 (DOCS\_PACKETS.md)

## 3.3

* 초인종 때문에 인터폰 상태 바뀔때 죽는 부분 수정
* MQTT로 임의의 serial packet 보내는 기능 추가 (디버그용)

## 3.2

* 같은 장치에 대한 명령을 동시에 여러개 받았을 때 죽는 경우 수정
* entrance\_mode: full 일때 가스밸브 상태 못받아오는 부분 수정

## 3.1

* 처음 설정하시는 분의 접근성을 위해 entrance\_mode 기본값을 off로 변경
    * 엘리베이터 호출을 사용하시려면 현관스위치 RS485 분리 후 entrance\_mode를 full로 변경하면 됩니다.
* 로그파일이 매 시간 덮어써지는 문제 수정

## 3

* 현관, 공동현관 초인종 이벤트 추가 (부엌/화장실 인터폰 있는 경우)
* dump 기능 추가
    * 패킷 분석이 필요할 때, 애드온 시작 전 정해진 시간 동안 패킷을 로깅할 수 있습니다.
* 로그를 share 디렉토리에 파일로 남기는 기능 추가

## 2.7

* gas\_valve sensor 수정
* checksum fail된 state는 반영하지 않도록 개선
* 시작할때 가끔 last\_query 없어서 죽는 현상 수정
* 특정 option이 없으면 default값으로 시도하도록 개선

## 2.4

* 실시간에너지 discovery 장치 오류 수정

## 2.3

* 명령 전송 타이밍 최적화
    * "last\_packet" 옵션은 삭제하였습니다.
* 몇몇 예외상황 처리

## 2.2

* 현관 스위치 기능들 discovery 추가
* 전등 discovery 오류 수정

## 2.1

* 실행 시 KeyError: 'prefix' 오류 수정
    * 업데이트 후 Configuration을 default로 돌렸다가 다시 설정하세요.
* share로 복사하는 동작 삭제

## 2

* serial 대신 **EW11 socket 통신 사용 가능**하도록 추가
    * socket 사용 시 엘리베이터 호출은 지원하지 않음
* **MQTT discovery 지원**, 이제 yaml을 만들 필요가 없습니다
* prefix 변경 옵션 추가

## 1

* HA Addon 등록 가능한 형태로 정리
* 설정 json 파일 분리

## 0

* .py 최초 공개
