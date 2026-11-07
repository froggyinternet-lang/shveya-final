# QR Печать Шаблон — PRM-2026-0001

## Размер стикера
- Общий: 30mm x 20mm
- QR поле: 15x15mm слева
- Текст справа: PRM-2026-0001 + дата
- Материал: полипропилен белый матовый, водостойкий, клей усиленный для ткани (не оставляет следов при снятии до 30 дней)

## Шаблон ZPL (Zebra)
```zpl
^XA
^FO20,20^BQN,2,4,M,7
^FDLA,PRM-2026-0001^FS
^FO90,20^A0N,20,20^FDPRM-2026-0001^FS
^FO90,45^A0N,15,15^FD2026-05-13^FS
^XZ
```

## Шаблон HTML для обычного принтера (A4 24 наклейки)
```html
<div style="width:30mm;height:20mm;border:0.5mm dashed #ccc;display:flex;align-items:center;padding:2mm">
  <div id="qrcode-PRM-2026-0001"></div>
  <div style="margin-left:2mm;font-family:monospace;font-size:8pt">
    PRM-2026-0001<br>13.05.2026
  </div>
</div>
<script src="https://cdn.jsdelivr.net/npm/qrcodejs@1.0.0/qrcode.min.js"></script>
<script>new QRCode(document.getElementById("qrcode-PRM-2026-0001"), {text:"PRM-2026-0001", width:60, height:60, correctLevel:QRCode.CorrectLevel.M});</script>
```

## Инструкция печати
1. Открыть /admin/items/PRM-2026-0001/qr
2. Нажать Печать QR
3. Выбрать принтер Zebra / обычный лазер
4. Проверить читаемость сканером
5. Наклеить внутрь шва, не на лицевую сторону
6. Сфоткать наклеенную QR как proof

## Частые проблемы
- Бледная печать → заменить риббон, повысить darkness 15→25
- Не читается → увеличить QR до 18mm, ECC Q
- Отклеивается → материал PET, не бумага

## Контроль
- Каждый 10-й стикер — тест скан
- Лог печати в events type='QR_PRINTED' idempotency_key='PRM-2026-0001:QR:<timestamp>'
