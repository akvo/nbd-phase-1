# Wetland Monitoring Platform — Solution Summary
**For:** Project partners and funders
**Date:** 2026-05-11
**Status:** Draft
**Derived from:** solution-design-technical.md v0.1

---

## 1. Executive Summary

The Nile Basin Discourse (NBD) and its partners are building a citizen-led data platform to monitor the health of two transboundary wetlands — the Mara Wetlands (Kenya/Tanzania) and the Sio-Siteko Wetland Landscape (Kenya/Uganda). The platform gives community members a simple way to report what they observe in and around the wetlands, aggregates that data into standardised health scores, and presents the results through a public portal that partners and government officials can use to take informed action.

The platform has two data collection workflows. In Kenya, community members called citizen reporters report pollution episodes and unusual events using their mobile phone — either via a basic USSD menu that works on any phone with a SIM card, or via a WhatsApp bot for smartphone users. In Tanzania, trained citizen scientists visit designated sampling sites once a month, take water quality measurements using a handheld probe, and submit structured data through the KoboCollect app, which works offline in areas with no internet coverage.

All data is reviewed and validated by Akvo staff, cross-checked by community meetings (Monthly Baraza), and periodically verified through laboratory analysis by academic partners. Validated results are displayed on the wetland data portal alongside satellite imagery, showing each wetland's current health class and the management actions that class requires.

---

## 2. What We're Building

The platform is a mobile-first data system built around the communities who live alongside the Mara and Sio-Siteko wetlands. It is not a replacement for formal monitoring — it is a structured, validated channel for the observations that community members are already making every day.

### Who uses it

| Who | What they do on the platform |
|-----|------------------------------|
| **Citizen reporters** (Kenya) | Report pollution episodes and unusual events using their mobile phone, via USSD or WhatsApp |
| **Citizen scientists** (Tanzania) | Record monthly water quality measurements and ecological observations using the KoboCollect app |
| **CSO staff** (UWASNET / KEWASNET) | Oversee data quality; manage citizen reporter and citizen scientist accounts |
| **Academic partners** (Makerere University / University of Nairobi) | Submit quarterly laboratory validation results |
| **NBD Secretariat, NDFs, County and District officials** | View wetland health scores, pollution incident maps, and management actions on the portal |

### What devices are needed

Citizen reporters need only a basic mobile phone with a SIM card to use the USSD channel. No internet, no app, no smartphone required. Citizen reporters with smartphones can also use WhatsApp.

Citizen scientists need an Android smartphone with the KoboCollect app installed. The app is free and works entirely offline — data is stored on the device and uploaded automatically when the phone reconnects to the internet. Citizen scientists also use a handheld multi-parameter probe (provided by the project) to measure pH, temperature, and dissolved oxygen at the sampling site.

---

## 3. How It Works

### 3.1 Reporting a Pollution Episode (Kenya — Citizen Reporters)

When a citizen reporter observes something unusual — a change in water colour or smell, an industrial discharge, flooding, encroachment, or overgrazing — they report it immediately using their mobile phone. No internet connection is required.

**If using a basic feature phone (no smartphone needed):**
1. Dial a short code
2. Navigate a simple menu: choose what happened and where
3. Submit — the final screen confirms the report was received and shows the contact details of the local KEWASNET representative

**If using a smartphone with WhatsApp:**
1. Open WhatsApp and start the wetland reporting bot
2. Follow menu prompts: choose the incident type and sub-county
3. Optionally add a photo with a GPS stamp or a voice note
4. Submit

In both cases the confirmation is part of the same interaction — the final USSD screen or the last WhatsApp message. No separate notification is sent. Akvo staff review each report, clean and tag it, and publish it to the wetland data portal once approved.

*[Simple flow diagram to be added]*

### 3.2 Monthly Water Quality Sampling (Tanzania — Citizen Scientists)

Once a month, each citizen scientist visits their designated sampling site with an Android smartphone and a handheld water quality probe. No internet connection is needed in the field — the app works offline and uploads the data automatically when connectivity is available.

1. **Arrive at the sampling site** (identified by a persistent site code, e.g. NBD-MARA-001)
2. **Open the KoboCollect app** — the form for that site loads, ready to fill in
3. **Take water quality measurements** using the handheld probe: pH, temperature, dissolved oxygen
4. **Record ecological observations**: papyrus density, bird sightings, fish catch, invasive plants
5. **Record hydrological observations**: water level, flow, flooding, encroachment signs
6. **Take GPS-stamped photographs** of the site
7. **Note any community knowledge** about changes observed at the site
8. **Submit the form** — it saves on the device until internet is available, then uploads automatically to the platform
9. Akvo staff review, score, and validate the data before it appears on the wetland data portal

Every three months, academic partners from Makerere University and the University of Nairobi independently sample the same sites in the laboratory to verify results and calibrate the citizen scientists' equipment.

*[Simple flow diagram to be added]*

### 3.3 The Wetland Data Portal — Seeing the Results

- The **wetland data portal** brings together all collected data in one place
- Key features visible on the portal:
  - A **pollution incident map** showing where and when episodes were reported
  - **Wetland health scores** for each sampling site, updated regularly
  - Trend views showing how wetland health changes over time
  - **Management actions** triggered by health status — colour-coded as Green (no action), Yellow (local community response), or Red (formal escalation to government authorities)
  - Satellite imagery (Sentinel 1 and 2) showing changes in vegetation, water extent, and land use as additional context
- Some information is publicly visible; detailed site data and individual records require a login

### 3.4 How Data Quality Is Maintained

The platform does not rely on technology alone for data quality. Three community-based mechanisms run in parallel:

- **Monthly Baraza** — a regular community meeting at which citizen reporters and citizen scientists review the data together, flag anomalies, and validate observations
- **Shadow sampling** — academic partners (Makerere University, University of Nairobi) periodically conduct independent sampling alongside citizen scientists to verify results
- **Lab QA** — water samples are sent to academic partner laboratories for independent chemical analysis (heavy metals, nutrients, biochemical oxygen demand)

---

## 4. Benefits & Outcomes

### For citizen reporters and citizen scientists
- A direct, structured channel to report what they observe — replacing informal complaints with validated records
- Confirmation that their report was received, with a contact for follow-up (KEWASNET representative)
- Visibility of the impact of their data through the wetland data portal

### For communities and water user associations
- Monthly Baraza meetings give communities a formal role in reviewing and validating the data before it is published
- The portal provides communities with health scores and trend data to support their own advocacy and decision-making
- A Red health status triggers formal escalation to government authorities — giving communities a documented enforcement pathway

### For CSOs (UWASNET / KEWASNET)
- A managed platform for overseeing data quality across their network of citizen reporters and citizen scientists
- Visibility of all submissions for their area, including flagged records requiring follow-up

### For NBD Secretariat, NDFs, County and District officials
- Regular, standardised wetland health data for two transboundary sites — updated monthly
- Pollution incident map showing where and when episodes have been reported
- Management actions structured around a traffic light classification, with clear escalation paths
- Data mapped to SDG 6.6.1 sub-indicators for national and international reporting
- Spatial layers available via API for integration with national data systems

### For academic partners and funders
- A validated, open-source platform that can be replicated at additional wetland sites beyond Phase 1
- Laboratory validation results integrated into the platform alongside citizen-collected data
- Demonstrated model for community-generated environmental data meeting scientific QA standards

---

*Full technical detail: [solution-design-technical.md](./solution-design-technical.md)*
