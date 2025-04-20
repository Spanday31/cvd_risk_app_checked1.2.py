
import streamlit as st
import math

interventions = [
    {"name": "Smoking cessation", "arr_lifetime": 17, "arr_5yr": 5},
    {"name": "Statin (atorvastatin 80 mg)", "arr_lifetime": 0, "arr_5yr": 0},
    {"name": "Ezetimibe", "arr_lifetime": 0, "arr_5yr": 0},
    {"name": "PCSK9 inhibitor", "arr_lifetime": 0, "arr_5yr": 0},
    {"name": "Antiplatelet (ASA or clopidogrel)", "arr_lifetime": 6, "arr_5yr": 2},
    {"name": "BP control (ACEi/ARB ± CCB)", "arr_lifetime": 12, "arr_5yr": 4},
    {"name": "Semaglutide 2.4 mg", "arr_lifetime": 4, "arr_5yr": 1},
    {"name": "Weight loss to ideal BMI", "arr_lifetime": 10, "arr_5yr": 3},
    {"name": "Empagliflozin", "arr_lifetime": 6, "arr_5yr": 2},
    {"name": "Icosapent ethyl (TG ≥1.5)", "arr_lifetime": 5, "arr_5yr": 2},
    {"name": "Mediterranean diet", "arr_lifetime": 9, "arr_5yr": 3},
    {"name": "Physical activity", "arr_lifetime": 9, "arr_5yr": 3},
    {"name": "Alcohol moderation", "arr_lifetime": 5, "arr_5yr": 2},
    {"name": "Stress reduction", "arr_lifetime": 3, "arr_5yr": 1}
]

ldl_effects = {
    "Statin (atorvastatin 80 mg)": 0.45,
    "Ezetimibe": 0.20,
    "PCSK9 inhibitor": 0.60
}

def scale_arr_by_age(base_arr, age):
    if age <= 50:
        return base_arr * 1.1
    elif age <= 60:
        return base_arr * 1.0
    elif age <= 70:
        return base_arr * 0.8
    else:
        return base_arr * 0.6

def estimate_smart_risk(age, sex, sbp, ldl, hdl, smoker, diabetes, egfr):
    sex_value = 1 if sex == "Male" else 0
    smoking_value = 1 if smoker else 0
    diabetes_value = 1 if diabetes else 0
    lp = (
        0.064 * age +
        0.34 * sex_value +
        0.02 * sbp +
        0.3 * ldl -
        0.25 * hdl +
        0.44 * smoking_value +
        0.51 * diabetes_value -
        0.2 * (egfr / 10)
    )
    baseline_survival = 0.900
    risk = 1 - baseline_survival ** math.exp(lp - 5.8)
    return round(risk * 100, 1)

def calculate_rrr(selected, age, ldl_current=None,
                  hba1c_current=None, hba1c_target=None,
                  sbp_current=None, sbp_target=None,
                  horizon="lifetime"):

    ldl_rrr = 0.0
    hba1c_rrr = 0.0
    sbp_rrr = 0.0
    lifestyle_rrr = 0.0

    selected_drugs = [interventions[i]["name"] for i, val in enumerate(selected) if val]
    ldl_factor = 1.0
    for drug in ldl_effects:
        if drug in selected_drugs:
            ldl_factor *= (1 - ldl_effects[drug])

    if ldl_current is not None:
        ldl_target = max(ldl_current * ldl_factor, 1.0)
        ldl_drop = max(ldl_current - ldl_target, 0)
        ldl_rrr = min(22 * ldl_drop, 35)
    else:
        ldl_target = None

    if hba1c_current is not None and hba1c_target is not None:
        effective_target = max(hba1c_target, 7.0)
        hba1c_drop = max(hba1c_current - effective_target, 0)
        hba1c_rrr = min(14 * hba1c_drop, 20)

    if sbp_current is not None and sbp_target is not None:
        sbp_drop = max(sbp_current - sbp_target, 0)
        sbp_rrr = min(20 * (sbp_drop / 10), 30)

    for i, selected_flag in enumerate(selected):
        name = interventions[i]["name"]
        if selected_flag and name not in ldl_effects:
            base_arr = interventions[i][f"arr_{horizon}"]
            adj_arr = scale_arr_by_age(base_arr, age)
            lifestyle_rrr += adj_arr

    lifestyle_rrr = min(lifestyle_rrr, 30)
    total_rrr = ldl_rrr + hba1c_rrr + sbp_rrr + lifestyle_rrr
    total_rrr = min(total_rrr, 70)

    return total_rrr, ldl_target

# Streamlit UI
st.title("CVD Risk Reduction Estimator")

age = st.slider("Age", 30, 90, 60)
sex = st.radio("Sex", ["Male", "Female"])
smoker = st.checkbox("Currently smoking")
diabetes = st.checkbox("Diabetes")
egfr = st.slider("eGFR (mL/min/1.73 m²)", 15, 120, 80)

horizon = st.radio("Select time horizon", ["5yr", "lifetime"], index=1)

ldl_current = st.number_input("Current LDL-C (mmol/L)", min_value=0.5, max_value=6.0, value=3.5, step=0.1)
hdl_current = st.number_input("Current HDL-C (mmol/L)", min_value=0.5, max_value=3.0, value=1.0, step=0.1)
hba1c_current = st.number_input("Current HbA1c (%)", min_value=4.5, max_value=12.0, value=8.0, step=0.1)
hba1c_target = st.number_input("Target HbA1c (%)", min_value=4.5, max_value=12.0, value=7.0, step=0.1)
sbp_current = st.number_input("Current SBP (mmHg)", min_value=80, max_value=220, value=145, step=1)
sbp_target = st.number_input("Target SBP (mmHg)", min_value=80, max_value=220, value=120, step=1)

st.markdown("### Select Interventions")
selection = [st.checkbox(intervention["name"], value=False) for intervention in interventions]

baseline_risk = estimate_smart_risk(age, sex, sbp_current, ldl_current, hdl_current, smoker, diabetes, egfr)

if st.button("Calculate Risk Reduction"):
    total_rrr, ldl_target = calculate_rrr(selection, age,
                                          ldl_current=ldl_current,
                                          hba1c_current=hba1c_current,
                                          hba1c_target=hba1c_target,
                                          sbp_current=sbp_current,
                                          sbp_target=sbp_target,
                                          horizon=horizon)

    final_risk = round(baseline_risk * (1 - total_rrr / 100), 1)
    arr = round(baseline_risk - final_risk, 1)

    st.success(f"SMART-estimated 10-year untreated risk: {baseline_risk}%")
    st.success(f"Estimated Cumulative ARR ({horizon}): {arr}%")
    st.info(f"Estimated Remaining CVD Risk: {final_risk}%")
    if ldl_target:
        st.warning(f"Estimated LDL-C target based on selected therapies: {ldl_target} mmol/L")
