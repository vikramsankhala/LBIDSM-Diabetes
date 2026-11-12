"""Descriptive thresholds, not autonomous treatment instructions."""
def observations(glucose=None, hba1c=None):
    findings = []
    if glucose is not None:
        if glucose < 54:
            findings.append("CGM reading below 54 mg/dL: level 2 hypoglycemia range; verify and follow established care plan.")
        elif glucose < 70:
            findings.append("CGM reading below 70 mg/dL: hypoglycemia range; verify and follow established care plan.")
        elif glucose > 250:
            findings.append("CGM reading above 250 mg/dL: marked hyperglycemia; interpretation depends on symptoms and clinical context.")
    if hba1c is not None and hba1c >= 6.5:
        findings.append("HbA1c meets a diabetes diagnostic criterion, subject to appropriate testing and confirmation; not an individualized treatment target.")
    return findings
