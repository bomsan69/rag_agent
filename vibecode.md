운영 환경을 아래와 같이 구성 하려고 합니다.

- 사무실에 있는 우분투 서버 이용
- 우분투 서버 ip은 192.168.100.232 사설 ip
- python 서버와, nextjs서버를 각각 8000과 4000port로 운영
- nextjs 서버는 colude fare Zero trust를 이용해서 https://meicare.aifreechtbot.com애 연결
- python 서버는 인터넷에 연결될 필요 없이 nextjs 서버와만 통신 하면됨
- 특히 nextjs에서 python 서버를 localhost:8000으로 호출해야 됨

위 내용을 고려해서 docker-compose.yml을 다시 검토해 주세요 

