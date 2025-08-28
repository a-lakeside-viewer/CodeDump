---
account: Silicom
model: Ibiza
part-number: 
station: 
failure-symptom: 
failure-specs: 
first-handled-on: <% tp.file.creation_date() %>
analysis: 
defect-location: 
action: 
tags:
  - "#Ibiza/qas"
to-do: Await unit's return 🧘🏽
icon: 👁️
current-station: Pre-FT
current-fs: Wait for Login
current-fspec: no console
unit-location: Quality Control Engineer
unit-status: For QAS 👁️
exampleProperty: ""
---
---
## 💡 Current Unit Status

| **Station Failed**              | **Failure Symptom**        | **Failure Specifications**    | **Unit Location**             | **Status**                  |
| ------------------------------- | -------------------------- | ----------------------------- | ----------------------------- | --------------------------- |
| `VIEW[{current-station}][text]` | `VIEW[{current-fs}][text]` | `VIEW[{current-fspec}][text]` | `VIEW[{unit-location}][text]` | `VIEW[{unit-status}][text]` |

## 🧠 Unit Info Switcher

```meta-bind-button
label: Refresh
icon: ""
style: default
class: ""
cssStyle: ""
backgroundImage: ""
tooltip: Refresh the buttons
id: refresh-button
hidden: false
actions:
  - type: command
    command: templater-obsidian:Templates/Modifier Templates/script-refresh-temp.md

```


**Part Number**
```meta-bind
INPUT[inlineSelect(
	option(80500-0240-G03-SL00),
	option(80500-0240-G03-SL01),
	option(80500-0240-G12-GT01),
	option(80500-0240-G13-SL01),
	option(80500-0240-G14-SL01),
	option(80500-0240-G17-NP02)
):part-number]
```

**Status**
`BUTTON[upd-stat-fa]` `BUTTON[upd-stat-su]`
`BUTTON[upd-stat-ft]` `BUTTON[upd-stat-fp]` `BUTTON[upd-stat-pbi]`
`BUTTON[upd-stat-sv]` `BUTTON[upd-stat-sc]`
`BUTTON[upd-stat-rw]` `BUTTON[upd-stat-npi]` `BUTTON[upd-stat-smt]` `BUTTON[upd-stat-pw]`
`BUTTON[upd-stat-qas]` `BUTTON[upd-stat-npi-qas]`


---

## 📒 Notes

1. 

---

## 👀 Visual Inspection Results

| ITEM NO. | COMPONENT TYPE (i.e. capacitor, resistor) | COMPONENT LOCATION | DEFECT | REMARKS | IMAGE/S |
| -------- | ----------------------------------------- | ------------------ | ------ | ------- | ------- |
| 1        |                                           |                    |        |         |         |

---

## ⚡ Power Sequencing 

| SEQUENCE | POWER RAIL                             | REFERENCE RESISTANCE | RESISTANCE | OUTPUT | INPUT | ENABLE | POWER GOOD | REMARKS |
| -------- | -------------------------------------- | -------------------- | ---------- | ------ | ----- | ------ | ---------- | ------- |
| 0        | 12V                                    | 648                  |            |        |       |        |            |         |
| 1        | P3V3_ALW_ON (U202)                     | 442                  |            |        |       |        |            |         |
| 2        | P1V8_ALW_ON (U387)                     | 82/7218              |            |        |       |        |            |         |
| 3        | P3V3A_DSW (U284)                       | 536                  |            |        |       |        |            |         |
| 4        | PCH_DPWROK (U313) (LEFT RESISTOR) (0V) | 200                  |            |        |       |        |            |         |
| 5        | P3V3A (U259)                           | 372                  |            |        |       |        |            |         |
| 6        | P5V0A (U390)                           | 422                  |            |        |       |        |            |         |
| 7        | VCCIN_AUX (U349) (1.8V)                | 57                   |            |        |       |        |            |         |
| 8        | P1V05_CPU (U334)                       | 67                   |            |        |       |        |            |         |
| 9        | P1V8U_VDD1 (U255)                      | 84                   |            |        |       |        |            |         |
| 10       | P1V065_VDD2 (U255)                     | 19                   |            |        |       |        |            |         |
| 11       | P0V5_VDDQ (U255)                       | 94                   |            |        |       |        |            |         |
| 12       | VCCANA (U317) (1V both sides)          | 104/2616             |            |        |       |        |            |         |
| 13       | P3V3S (U258)                           | 528                  |            |        |       |        |            |         |
| 14       | P1V8S (U260)                           | 83                   |            |        |       |        |            |         |
| 15       | VCCCORE (U249, U250) (0.94V then 0.7V) | 11                   |            |        |       |        |            |         |

#### Probe Map & Full Sequence
![[Ibiza Power Sequence.png]]
![[Full Power Sequence.png]]

---

## 🍌 Non-wetting CPU Checks

	NOTE: FACING BGA UNLESS STATED

| LOCATION | G12 RESISTANCE | G17 RESISTANCE | UNIT RESISTANCE |
| -------- | -------------- | -------------- | --------------- |
| R2596    | 33169          | 51323          |                 |
| R2598    | 10587          | 10600          |                 |
| R2593    | 33371          | 32381          |                 |
| R2591    | 33326          | 53032          |                 |
| R2516    | 32136          | 35912          |                 |
| R2509    | 32300          | 35932          |                 |
| R2518    | 33168          | 56342          |                 |
| R2513    | 32557          | 45855          |                 |
| R2510    | 32421          | 35838          |                 |
| R2514    | 32424          | 36016          |                 |
| R2511    | 32370          | 35982          |                 |
| R2175    | 10434          | 10460          |                 |
| R496     | 99             | 98             |                 |
| R1527    | 38965          | 39690          |                 |
| R1528    | 38951          | 39640          |                 |
| R2582    | 38917          | 39578          |                 |
| R2581    | 38963          | 39630          |                 |
| R536     | 113            | 113            |                 |
| R3095    | 10430          | 10410          |                 |
| R2569    | 3859           | 6170           |                 |
| R2542    | 10619          | 10595          |                 |
| R1763    | 47020          | 34808          |                 |
| R2594    | 33064          | 33909          |                 |
| R3214    | 32743          | 33586          |                 |
| C1923    | 23403          | 33056          |                 |
| R2544    | 34094          | 34935          |                 |
| C1922    | 262            | 435            |                 |
| R2424    | 200            | 200            |                 |
| R522     | 150            | 150            |                 |
| R600     | 59440 / 3.8MOhm | 68924 / 5.25MOhm |                 |


---

## 👨🏽‍🏭 Actions, Results, and Thoughts

| DATE & TIME | ACTION |
| ----------- | ------ |
|             |        

---

## 💻 Tera Term Commands

##### G12

`BUTTON[G12PreFTSeq]` `BUTTON[G12PreUSBSeq]` `BUTTON[G12FTSeq]`
`BUTTON[G12BISeq]` `BUTTON[G12PBISeq]`


##### G17


`BUTTON[G17PreFTSeq]` `BUTTON[G17PreUSBSeq]` `BUTTON[G17FTSeq]`
`BUTTON[G17LTESeq]` `BUTTON[G17BISeq]` `BUTTON[G17PBISeq]`


---

## 🖱️Widgets

###### Buttons
```meta-bind-button
label: For Failure Analysis 🔍
icon: ""
style: default
class: ""
cssStyle: ""
backgroundImage: ""
tooltip: Unit is for analysis
id: upd-stat-fa
hidden: false
actions:
  - type: runTemplaterFile
    templateFile: Templates/Modifier Templates/upd-stat-fa-temp.md
```

```meta-bind-button
label: For Testing ⌛
icon: ""
style: default
class: ""
cssStyle: ""
backgroundImage: ""
tooltip: Unit is for testing
id: upd-stat-ft
hidden: false
actions:
  - type: runTemplaterFile
    templateFile: Templates/Modifier Templates/upd-stat-ft-temp.md
```

```meta-bind-button
label: Failure Passed 💪🏽
icon: ""
style: default
class: "green-button"
cssStyle: ""
backgroundImage: ""
tooltip: Unit has passed the failure
id: upd-stat-fp
hidden: false
actions:
  - type: runTemplaterFile
    templateFile: Templates/Modifier Templates/upd-stat-fp-temp.md
```

```meta-bind-button
label: PBI Passed 😎🏆
icon: ""
style: primary
class: ""
cssStyle: ""
backgroundImage: ""
tooltip: Unit has passed the final station
id: upd-stat-pbi
hidden: false
actions:
  - type: runTemplaterFile
    templateFile: Templates/Modifier Templates/upd-stat-pbi-temp.md
```

```meta-bind-button
label: For Scrap Verification 😱
icon: ""
style: default
class: ""
cssStyle: ""
backgroundImage: ""
tooltip: Unit is for scrap verification
id: upd-stat-sv
hidden: false
actions:
  - type: runTemplaterFile
    templateFile: Templates/Modifier Templates/upd-stat-sv-temp.md
```

```meta-bind-button
label: Unit Stored 📦
icon: ""
style: default
class: ""
cssStyle: ""
backgroundImage: ""
tooltip: Unit is stored for now
id: upd-stat-su
hidden: false
actions:
  - type: runTemplaterFile
    templateFile: Templates/Modifier Templates/upd-stat-su-temp.md
```

```meta-bind-button
label: Scrap Verified ☠️☠️
icon: ""
style: destructive
class: ""
cssStyle: ""
backgroundImage: ""
tooltip: Unit is confirmed as scrap
id: upd-stat-sc
hidden: false
actions:
  - type: runTemplaterFile
    templateFile: Templates/Modifier Templates/upd-stat-sc-temp.md
```

```meta-bind-button
label: For NPI Rework 🌑
icon: ""
style: default
class: ""
cssStyle: ""
backgroundImage: ""
tooltip: Unit for NPI rework
id: upd-stat-npi
hidden: false
actions:
  - type: runTemplaterFile
    templateFile: Templates/Modifier Templates/upd-stat-npi-temp.md
```

```meta-bind-button
label: For SMT Rework ⛏️
icon: ""
style: default
class: ""
cssStyle: ""
backgroundImage: ""
tooltip: Unit for SMT rework
id: upd-stat-smt
hidden: false
actions:
  - type: runTemplaterFile
    templateFile: Templates/Modifier Templates/upd-stat-smt-temp.md
```

```meta-bind-button
label: For Rework 🛠️
icon: ""
style: default
class: ""
cssStyle: ""
backgroundImage: ""
tooltip: Unit for FA rework
id: upd-stat-rw
hidden: false
actions:
  - type: runTemplaterFile
    templateFile: Templates/Modifier Templates/upd-stat-rw-temp.md
```

```meta-bind-button
label: For Parts Withdrawal 🏦
icon: ""
style: default
class: ""
cssStyle: ""
backgroundImage: ""
tooltip: Unit for Parts Withdrawal
id: upd-stat-pw
hidden: false
actions:
  - type: runTemplaterFile
    templateFile: Templates/Modifier Templates/upd-stat-pw-temp.md
```

```meta-bind-button
label: G12 Pre-FT
icon: ""
style: default
class: ""
cssStyle: ""
backgroundImage: ""
tooltip: ""
id: G12PreFTSeq
hidden: false
actions:
  - type: open
    link: obsidian://open?vault=Ionics%20New&file=Accounts%2FSilicom%2FIbiza%2FSequence%20Commands%2F80500-0240-G12%2FR201%2F80500-0240-G12_PreFT_100.csv
    newTab: true

```

```meta-bind-button
label: G12 Pre-USB
icon: ""
style: default
class: ""
cssStyle: ""
backgroundImage: ""
tooltip: ""
id: G12PreUSBSeq
hidden: false
actions:
  - type: open
    link: obsidian://open?vault=Ionics%20New&file=Accounts%2FSilicom%2FIbiza%2FSequence%20Commands%2F80500-0240-G12%2FR201%2F80500-0240-G12_PreUSB_102.csv
    newTab: true

```

```meta-bind-button
label: G12 FT
icon: ""
style: default
class: ""
cssStyle: ""
backgroundImage: ""
tooltip: ""
id: G12FTSeq
hidden: false
actions:
  - type: open
    link: obsidian://open?vault=Ionics%20New&file=Accounts%2FSilicom%2FIbiza%2FSequence%20Commands%2F80500-0240-G12%2FR201%2F80500-0240-G12_FT_104.csv
    newTab: true

```

```meta-bind-button
label: G12 BI
icon: ""
style: default
class: ""
cssStyle: ""
backgroundImage: ""
tooltip: ""
id: G12BISeq
hidden: false
actions:
  - type: open
    link: obsidian://open?vault=Ionics%20New&file=Accounts%2FSilicom%2FIbiza%2FSequence%20Commands%2F80500-0240-G12%2FR201%2F80500-0240-G12_24h_100.csv
    newTab: true

```

```meta-bind-button
label: G12 PBI
icon: ""
style: default
class: ""
cssStyle: ""
backgroundImage: ""
tooltip: ""
id: G12PBISeq
hidden: false
actions:
  - type: open
    link: obsidian://open?vault=Ionics%20New&file=Accounts%2FSilicom%2FIbiza%2FSequence%20Commands%2F80500-0240-G12%2FR201%2F80500-0240-G12_PostBI_102.csv
    newTab: true

```

```meta-bind-button
label: G17 Pre-FT
icon: ""
style: default
class: ""
cssStyle: ""
backgroundImage: ""
tooltip: ""
id: G17PreFTSeq
hidden: false
actions:
  - type: open
    link: obsidian://open?vault=Ionics%20New&file=Accounts%2FSilicom%2FIbiza%2FSequence%20Commands%2F80500-0240-G17%2FR203%2F80500-0240-G17_PreFT_101.csv
    newTab: true

```

```meta-bind-button
label: G17 Pre-USB
icon: ""
style: default
class: ""
cssStyle: ""
backgroundImage: ""
tooltip: ""
id: G17PreUSBSeq
hidden: false
actions:
  - type: open
    link: obsidian://open?vault=Ionics%20New&file=Accounts%2FSilicom%2FIbiza%2FSequence%20Commands%2F80500-0240-G17%2FR203%2F80500-0240-G17_PreUSB_100.csv
    newTab: true

```

```meta-bind-button
label: G17 FT
icon: ""
style: default
class: ""
cssStyle: ""
backgroundImage: ""
tooltip: ""
id: G17FTSeq
hidden: false
actions:
  - type: open
    link: obsidian://open?vault=Ionics%20New&file=Accounts%2FSilicom%2FIbiza%2FSequence%20Commands%2F80500-0240-G17%2FR203%2F80500-0240-G17_FT_103.csv
    newTab: true

```

```meta-bind-button
label: G12 BI
icon: ""
style: default
class: ""
cssStyle: ""
backgroundImage: ""
tooltip: ""
id: G12BISeq
hidden: false
actions:
  - type: open
    link: obsidian://open?vault=Ionics%20New&file=Accounts%2FSilicom%2FIbiza%2FSequence%20Commands%2F80500-0240-G17%2FR203%2F80500-0240-G17_24h_101.csv
    newTab: true

```

```meta-bind-button
label: G17 LTE
icon: ""
style: default
class: ""
cssStyle: ""
backgroundImage: ""
tooltip: ""
id: G17LTESeq
hidden: false
actions:
  - type: open
    link: obsidian://open?vault=Ionics%20New&file=Accounts%2FSilicom%2FIbiza%2FSequence%20Commands%2F80500-0240-G17%2FR203%2F80500-0240-G17_LTE_100.csv
    newTab: true

```

```meta-bind-button
label: G17 PBI
icon: ""
style: default
class: ""
cssStyle: ""
backgroundImage: ""
tooltip: ""
id: G17PBISeq
hidden: false
actions:
  - type: open
    link: obsidian://open?vault=Ionics%20New&file=Accounts%2FSilicom%2FIbiza%2FSequence%20Commands%2F80500-0240-G17%2FR203%2F80500-0240-G17_PostBI_102.csv
    newTab: true

```

```meta-bind-button
label: For QAS 👁️
icon: ""
style: default
class: ""
cssStyle: ""
backgroundImage: ""
tooltip: Unit for QAS
id: upd-stat-qas
hidden: false
actions:
  - type: runTemplaterFile
    templateFile: Templates/Modifier Templates/upd-stat-qas-temp.md
```

```meta-bind-button
label: For NPI QAS 🌑👁️
icon: ""
style: default
class: ""
cssStyle: ""
backgroundImage: ""
tooltip: Unit for NPI QA
id: upd-stat-npi-qas
hidden: false
actions:
  - type: runTemplaterFile
    templateFile: Templates/Modifier Templates/upd-stat-npq-temp.md
```

