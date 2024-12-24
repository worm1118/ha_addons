# 삼성SDS 월패드 RS485 Add-on (엘리베이터 호출 지원) TUNA modified

![Supports aarch64 Architecture][aarch64-shield] ![Supports amd64 Architecture][amd64-shield] ![Supports armhf Architecture][armhf-shield] ![Supports armv7 Architecture][armv7-shield] ![Supports i386 Architecture][i386-shield]

## 소개

* [버전별 변경 사항](https://github.com/n-andflash/ha_addons/blob/master/sds_wallpad/CHANGELOG.md)

* 삼성SDS 월패드를 사용하는 집에서, RS485를 이용해 여러 장치들을 제어할 수 있는 애드온입니다.
* 현관 스위치를 대신하여 엘리베이터를 호출하는 기능이 있습니다.
* MQTT discovery를 이용, 장치별로 yaml 파일을 직접 작성하지 않아도 집에 있는 모든 장치가 HA에 자동으로 추가됩니다.

## 지원

* 정확한 지원을 위해서, 글을 쓰실 때 아래 사항들을 포함해 주세요.
    * 실행 로그 (HA의 share 폴더에 최신 로그 파일 (날짜가 써있지 않은 sds\_wallpad.log 파일) 이 있습니다)
    * Configuration 페이지 내용 (MQTT broker password가 있으면 가려주세요)
* 집마다 패킷이나 장치 구성이 다르므로, 해결을 위해 여러 번의 추가정보 확인 요청이 필요할 수 있습니다.

[HomeAssistant 네이버 카페 (질문, 수정 제안 등)](https://cafe.naver.com/koreassistant)

[Github issue 페이지 (버그 신고, 수정 제안 등)](https://github.com/n-andflash/ha_addons/issues)

[삼성SDS 월패드 RS485 패킷 분석](https://github.com/n-andflash/ha_addons/blob/master/sds_wallpad/DOCS_PACKETS.md)

## 면책조항 (Disclaimer)

* 이 애드온은 무상으로 제공되므로 정확성이나 안정성 등 어떠한 보증도 제공하지 않습니다.
* 이 애드온은 오픈소스로 실행 코드와 함께 배포되므로 코드 및 동작에 대한 확인 책임은 사용자에게 있습니다.
* 기타 사항은 GPLv3를 따릅니다. [전문보기](https://github.com/n-andflash/ha_addons/raw/master/sds_wallpad/LICENSE)

---

![카카오톡 후원 QR코드](https://github.com/n-andflash/ha_addons/raw/master/sds_wallpad/images/donation_kakao.png)
* 카카오톡 후원 코드: https://qr.kakaopay.com/281006011000008548744237 (모바일에서만 가능)

[aarch64-shield]: https://img.shields.io/badge/aarch64-yes-green.svg
[amd64-shield]: https://img.shields.io/badge/amd64-yes-green.svg
[armhf-shield]: https://img.shields.io/badge/armhf-yes-green.svg
[armv7-shield]: https://img.shields.io/badge/armv7-yes-green.svg
[i386-shield]: https://img.shields.io/badge/i386-yes-green.svg
