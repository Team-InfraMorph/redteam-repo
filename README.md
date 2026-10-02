# redteam-repo

개발을 시작하기 전에 [협업 규칙 및 Git 훅 설치](CONTRIBUTING.md)를 확인하세요.

## Policy 검증 입력 (E)

정상 대조군 9개와 공격·위반 입력 30개, 총 39개를 제공합니다. 실제 방어 코드는 `inframorph`에서 구현합니다.

```sh
python3 -m unittest discover -s tests -p 'test_fixtures.py' -v
```

[입력 목록·기대 결과·통합 방법](docs/policy-fixtures.md)을 확인하세요.
현재 검사는 **입력 자료의 무결성 검사**이며 실제 Agent/Policy Gate 통합 검증은 미완료입니다.

[설계 목적과 담당 경계](docs/policy-direction.md) · [병합 준비도 재평가](docs/pr-readiness.md)
