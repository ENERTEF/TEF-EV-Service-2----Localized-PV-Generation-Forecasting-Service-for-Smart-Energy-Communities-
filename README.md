# Localized PV Generation Forecasting Service for Smart Energy Communities (ECC)

**Service:** Localized PV Generation Forecasting Service
**TEF:** TEF EV – Leneda (Luxembourg)
**End User:** EMOT EMOTION SRL
**Site:** Copal Supermarket Energy Community (ECC)
**Version:** 1
**Last Updated:** 20 Jan 2026

---

# Overview

The **Localized PV Generation Forecasting Service (ECC)** provides high-resolution **short-term and day-ahead forecasts of photovoltaic (PV) power generation** for an energy community operating under a **settlement-aware sharing scheme (ACR)**.

The service is tailored to the **ECC (Copal Supermarket)** site and delivers forecasts compatible with:

* community-level energy planning
* EV-ready operational decision making
* optimization services such as **EV charging flexibility orchestration**

Accurate local PV forecasts are essential for communities that rely on **solar generation as a primary energy source** while operating **flexible loads such as EV charging infrastructure**.

PV intermittency can lead to:

* underutilized clean energy
* unexpected grid exports
* increased supplier dependency

This service enables stakeholders to:

* anticipate PV availability and improve operational scheduling
* align flexible demand (EV charging) with expected PV generation
* reduce export peaks (“reverse flow” proxies)
* increase self-consumption within the community
* improve community autonomy and reduce supplier invoicing

The service operates at **15-minute resolution**, consistent with **Leneda dataset exports and TEF EV metering conventions**.

The forecasting framework incorporates **physics-informed feature engineering**, including:

* irradiance transposition
* inverter capacity constraints
* ramp-rate modeling
* optional shading-aware adjustments

Forecast outputs may include **deterministic and probabilistic components** to support **risk-aware scheduling and downstream MPC integration**.

---

# 1. Business Context & Definitions

| Term                         | Definition                                                                 |
| ---------------------------- | -------------------------------------------------------------------------- |
| **ECC / Site**               | Energy Community Copal Supermarket (ECC case in Leneda dataset)            |
| **PV Plant**                 | Photovoltaic installation producing active power measured at site level    |
| **Timestamp / Started at**   | Start of each 15-minute interval in ISO-8601 format (timezone included)    |
| **Forecast horizon**         | Time window ahead for which PV power is predicted (typically 24–48 hours)  |
| **Resolution / Granularity** | 15-minute forecast step aligned to Leneda interval length                  |
| **AC Power**                 | Measured PV production in kW (active production)                           |
| **Uncertainty / Quantiles**  | Optional probabilistic forecasts (P10/P50/P90)                             |
| **Backtesting**              | Rolling historical evaluation emulating real-time forecast issuance        |
| **Forecast package**         | Structured forecast output including predictions, issue time, and metadata |

---

# 1.1 ECC (Community Context)

This service supports **Copal Supermarket Energy Community (ECC)** by strengthening **operational planning and PV-aware energy coordination**.

ECC characteristics:

| Parameter         | Value                                       |
| ----------------- | ------------------------------------------- |
| PV plant capacity | ~1 MW (973.81 kWc)                          |
| Coordinates       | 6.48714 E, 49.70673 N                       |
| EV chargers       | 16 installed                                |
| Sharing scheme    | ACR (Collective Renewable Self-Consumption) |

The EV charging optimization is handled by **a separate service**, but this forecasting service provides critical input data for such coordination.

ECC can use PV forecasts to:

* anticipate PV ramps and variability
* schedule flexible loads such as EV charging
* reduce exported PV energy
* improve self-consumption performance
* support reporting through **forecast vs measured production comparisons**

---

# 2. Problem Statement

The objective is to deliver a **reliable production-grade forecasting service** that predicts **ECC PV generation at 15-minute resolution** for horizons up to **24–48 hours ahead**.

Supported forecast horizons may include:

| Horizon           | Typical Range |
| ----------------- | ------------- |
| Short-term        | 1–6 hours     |
| Day-ahead         | 24–48 hours   |
| Optional extended | up to 7 days  |

Operational focus remains on **short-term and day-ahead forecasts**, which are required for **Model Predictive Control (MPC)** scheduling.

The service must:

1. provide accurate and stable PV forecasts under changing weather conditions
2. expose an authenticated interface for requesting forecasts by site and time range
3. return time-aligned outputs with issue time and traceability metadata
4. support backtesting and performance monitoring
5. ensure forecasts remain within realistic **physical limits** (e.g., not exceeding plant capacity)

---

# 3. Data Description

## 3.1 Data Sources (ECC)

The forecasting system integrates **three categories of inputs**.

### A. Internal / Private Inputs

Historical PV performance data.

Examples:

* measured PV active production time series (kW)
* plant operating characteristics derived from historical data

  * seasonality
  * ramp behavior
  * production envelopes

---

### B. Meteorological Forecast Inputs

External weather forecasts are used as **exogenous drivers**.

Typical variables include:

* Global Horizontal Irradiance (GHI)
* Direct Normal Irradiance (DNI)
* Diffuse Horizontal Irradiance (DHI)
* Plane-of-Array irradiance estimation
* Ambient temperature
* Humidity
* Cloud cover and cloud type
* Aerosol optical depth
* Wind speed (panel cooling proxy)
* Sun elevation and azimuth angles

Example data sources:

* Open Meteo
* ECMWF-based forecasts
* MeteoLux

---

### C. PV System Metadata

Site-specific configuration information.

| Parameter         | Value                                        |
| ----------------- | -------------------------------------------- |
| Nominal capacity  | 973.81 kWc                                   |
| Coordinates       | 6.48714 E, 49.70673 N                        |
| Optional metadata | Tilt, azimuth, shading, curtailment settings |

---

### Input Record Schema

Each record contains:

| Field                         | Description                 |
| ----------------------------- | --------------------------- |
| Metering point                | Unique POD identifier       |
| OBIS code                     | Signal identifier           |
| Unit                          | kW                          |
| Started at                    | Timestamp of interval start |
| Value                         | Numeric measurement         |
| Interval length (min)         | Expected 15                 |
| Estimated / measured / edited | Data quality flag           |
| Version                       | Revision index              |

---

## 3.2 Data Dictionary

| Signal                        | OBIS code  | CSV file            | Unit | Purpose                         |
| ----------------------------- | ---------- | ------------------- | ---- | ------------------------------- |
| Measured active PV production | 1-1:2.29.0 | ECC_PV_Active_P.csv | kW   | Target variable for forecasting |

**Physical constraints**

PV output is bounded by:

* plant nominal capacity: **973.81 kWc**
* meteorological conditions
* inverter limits and operational constraints

---

# 4. Analytics Scope & Update Frequency

## Temporal Scope

| Parameter         | Value                  |
| ----------------- | ---------------------- |
| Forecast horizons | Short-term + day-ahead |
| Default horizon   | 24 hours               |
| Optional horizon  | 48 hours               |
| Resolution        | 15 minutes             |

All forecasts are aligned with **Leneda dataset export intervals**.

---

## Update Frequency

Forecast generation can occur:

* **on demand via API request** (recommended for integration)
* on a **fixed cadence**

  * hourly
  * every 15 minutes

---

## Forecast Output Package

Each forecast run returns:

* **issue time (UTC)**
* forecast validity window
* time-indexed PV production forecast (kW)
* optional probabilistic forecasts:

  * P10
  * P50
  * P90
* traceability metadata:

  * forecast ID
  * model version
  * input dataset coverage flags

Additional derived indicators may include:

* peak generation timing and magnitude
* ramp-rate forecast (kW per interval)
* clear-sky reference generation estimate
* forecast skill score vs persistence baseline

---

# 5. Evaluation Protocols & Metrics

Evaluation ensures the service produces **consistent and operationally reliable forecasts**.

---

## 5.1 Forecasting Protocol

Evaluation follows these rules:

* forecasts use only information available at **issue time**
* outputs align with a **consistent 15-minute time grid**
* repeated calls with identical inputs produce consistent outputs
* historical **rolling backtesting** is used for validation

Additional evaluation checks include:

* forecast bias (systematic over- or under-prediction)
* forecast skill relative to persistence
* peak generation timing error
* ramp prediction accuracy
* probabilistic reliability (coverage of confidence intervals)

Operational performance target:

* **API latency < 5 seconds** for short-term forecasts

---

## 5.2 Data Gaps & Exceptions

Handling rules:

* intervals flagged as **missing, invalid, or estimated** may be excluded from evaluation
* insufficient data coverage triggers:

  * structured error responses
  * documented fallback behavior

---

## 5.3 Service Evaluation Metrics

### Forecast Quality Metrics

Evaluated per forecast horizon:

* 1-hour horizon
* 6-hour horizon
* day-ahead horizon

Metrics include:

* RMSE
* MAE / nMAE
* R² (coefficient of determination)

---

### Service Performance Metrics

Operational KPIs include:

* availability / uptime of forecast endpoints
* request latency
* reliability of forecast delivery

---

# 6. Deliverables & Submissions

The service lifecycle includes **three reporting stages**.

---

## 6.1 Deliverable Reports

### 1️⃣ Pre-Service Deliverable – Service Design & Setup Report

Includes:

* forecasting approach (baseline + advanced ML methods)
* weather provider integration plan
* feature engineering strategy
* data cleaning and alignment procedures
* physical constraint enforcement
* API design and security model
* auditability and versioning
* fallback strategies and limitations

---

### 2️⃣ Intermediate Deliverable – Interim Performance & Operations Report

Includes:

* dataset coverage and completeness statistics
* preliminary forecast performance metrics

  * RMSE
  * nMAE
  * bias
* operational insights

  * ramp periods
  * seasonal variability
* model improvements

  * feature additions
  * model upgrades

---

### 3️⃣ Final Deliverable – Final Evaluation & Recommendations Report

Includes:

* final performance summary across horizons
* stability and robustness analysis
* recommendations for scaling to multiple PV sites
* readiness for integration with **EV scheduling and MPC optimization**

---

## 6.2 Technical Specifications & Submissions

Required technical artifacts include:

* **Service interface documentation**

  * API endpoints
  * request/response schemas
  * authentication

* **Deployment artifacts**

  * Docker / containerization
  * or documented environment setup

* **Configuration and versioning guide**

  * model retraining schedule
  * model versions
  * run IDs and audit metadata

* **Security and data protection documentation**

  * data handling procedures
  * access control policies
  * compliance with data protection requirements

