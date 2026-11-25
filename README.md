# 季节性宽带场所迁装的服务接续与计费

地址和入户点是演练代号，时间以同一账期的相对日表示。可用、装完和用户验收是不同事件，可以由不同方报告。

所有资料供本地联调，为合成记录。`samples/register.json` 是基础台账，`samples/intake.json` 是送达的业务事实，`samples/receipts.json` 是对端查询合同。

## 本地资料端

使用 Python 3.11.2 标准库。服务只监听回环地址。

```sh
python3 -m unittest -v
python3 partner_feed.py --port 8765
```

- `GET /register` 读取台账。
- `GET /intake?since=0&limit=50` 读取一页到达记录，将返回的 `cursor` 传给下一次查询的 `since`。消息含 `sequence`、`at`、`source`、`facts`，其中 `at` 是收到记录的时间，业务发生时间可在 `facts` 中明确报告。
- `GET /receipt?action=操作&desk=经办方&ref=编号` 以三项值匹配样例。对端返回 `evidence` 作为独立事实。标记 `delayed` 的样例首次查询返回 503，后续可以读取回执。未知编号返回 404。联调端不会自行办理业务操作。

通过 `--samples` 指定另一组同名资料可换样例。临时不可查的状态按联调进程保存。
