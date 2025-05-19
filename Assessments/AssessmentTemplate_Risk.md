# Risk Assessment Header

- Assessment Period
- Last Known Baseline
- Narrative on Assessment Results

## Context Assessment

- Description of context in contrast to known baseline
- If else, establish **Baseline Context** 

### Categories of Context
- Global
- Domestic
- Local
- Functional
- Individual

#### Relevance of Context

- Disclosure of Context **Assumptions** 
- Disclosure of **Tradeoffs** in Context Selection

## Description of Assessment Item

- Common Domain Specific Language (**CDSL**) description of **Item** in terms of **Outputs** to **Stakeholders**

### Strategic Description

- Common Domain Specific Language (**CDSL**) description of Item in terms of Outputs (**CDTO**) to **Customers** and **Internal Stakeholders** and **Shareholders**

### Tactical Description

- CSDL description of Item in terms of Process (**CDTP**) to Internal Stakeholders (**First Line Operators**, **Second Line Operators**, **Third Line Operators**)
- Risk Domain Specific Language in terms of Trade-Offs to **Process** **Design**
- Risk and Control Domain Specific Language in terms of **Inherent Risk**, **Control** **Effectiveness**, and **Residual Risk**

## Rating Scales

Use a consistent five-point scale to score the severity of inherent risk and the effectiveness of controls:

| Score | Descriptor | Description |
| ----- | ---------- | ----------- |
| 1 | Low | Minimal impact or probability |
| 2 | Minor | Limited impact; unlikely to occur |
| 3 | Moderate | Noticeable impact; possible occurrence |
| 4 | Major | Serious impact; likely to occur |
| 5 | Severe | Critical impact; near certain occurrence |

Control effectiveness may reuse the same scale where **1** means ineffective and **5** means highly effective.

### Residual Risk Calculation

Residual Risk can be estimated by combining the inherent risk score with the inverse of the control effectiveness score:

```
Residual Risk = Inherent Risk × (6 - Control Effectiveness)
```

The resulting value is mapped back to the rating scale to determine the final risk level.

### Example Risk Table

| Assessment Item | Inherent Risk | Control Effectiveness | Residual Risk |
| --------------- | ------------- | -------------------- | ------------- |
| Example Process | 4 | 3 | 12 |

Residual risk scores above the organization's tolerance may trigger additional mitigation steps, such as stronger controls or risk transfer.

### Risk Response

- **Accept** – residual risk is within tolerance.
- **Mitigate** – implement additional controls to reduce risk.
- **Transfer** – share risk with another party (e.g., insurance or outsourcing).
- **Avoid** – discontinue the activity to eliminate the risk.
