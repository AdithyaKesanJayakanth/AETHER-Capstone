# Reference data

| File | Source | Content |
|---|---|---|
| `NASA_TM_X-1243_Bertin_1966.pdf` | Bertin, J. J., *The Effect of Protuberances, Cavities, and Angle of Attack on the Wind-Tunnel Pressure and Heat-Transfer Distribution for the Apollo Command Module*, NASA TM X-1243, Oct. 1966. https://ntrs.nasa.gov/citations/19660028003 | Clean Apollo CM geometry (Fig. 1b), pressure (Fig. 3a) and heating (Fig. 8a) distributions at alpha = 0, M = 10.18, Re_D = 1.1e6, AEDC Tunnel C |
| `bertin_tmx1243_fig3a_pressure.csv` | digitised from Fig. 3(a) | p_l/p_t vs S/R |
| `bertin_tmx1243_fig8a_heating.csv` | digitised from Fig. 8(a) | q/q_t vs S/R (range of data) |
| `NASA_TM_100484_Wieting_1987.pdf` (not committed, 103 MB; download from https://ntrs.nasa.gov/citations/19870017721) | Wieting, A. R., *Experimental Study of Shock Wave Interference Heating on a Cylindrical Leading Edge*, NASA TM 100484, May 1987 | Undisturbed-flow baseline Run 31 (Calspan 48-inch HST): Table 11 test conditions, Appendix E tabulated p/P0 and q/Q0 |
| `wieting_run31_pressure.csv`, `wieting_run31_heatflux.csv` | transcribed from the Appendix E "RUN 31" page | p/P0 and q/Q0 vs theta |

Run 31 test conditions (Table 11 of TM 100484): M = 8.03, p_inf = 0.124 psia, rho_inf = 1.501e-3 lbm/ft^3, T_inf = 224.9 R, u_inf = 5907 ft/s, Re_inf = 1.468e6 /ft, h_T = 1.878e7 ft^2/s^2, T_T = 2849 R, P_T = 1411 psia. Heat-transfer data corrected to a uniform wall temperature of 530 R (Appendix E). Normalising values for Run 31: Q0 = 63.49 Btu/ft^2-s, P0 = 10.47 psia. Cylinder diameter 3.0 in.

Digitised values carry the reading uncertainty stated in each file header; they are used for comparison plots and percent differences, never as inputs to the simulations.
