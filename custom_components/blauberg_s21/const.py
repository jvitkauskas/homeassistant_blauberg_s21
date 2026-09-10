"""Constants for the Blauberg S21 integration."""

DOMAIN = "blauberg_s21"

# Coils
CL_POWER = 0
CL_Boost_MODE = 3
CL_BoostSWITCH_CTRL = 13
CL_RESET_FILTER_TIMER = 17
CL_RESET_ALARM = 18

# Holding registers
HR_MaxSPEED_MODE = 1
HR_SPEED_MODE = 2
HR_ManualSPEED = 17
HR_OPERATION_MODE = 43
HR_SetTEMP = 44

# Input registers
IR_CurTEMP_SuAirIn = 1  # Outdoor air, before pre-heating
IR_CurTEMP_SuAirOut = 2  # Supply air, at unit outlet
IR_CurTEMP_ExAirIn = 3  # Extract air (from the rooms), at unit inlet
IR_CurTEMP_ExAirOut = 4  # Exhaust air (to the outside), at unit outlet
IR_CurRH_Int = 10
IR_CurSuAirFLOW = 19
IR_CurExAirFLOW = 20
IR_CurSuPRESS = 21  # Pressure in the supply air duct, Pa
IR_CurExPRESS = 22  # Pressure in the extract air duct, Pa
IR_SuRPM = 23
IR_ExRPM = 24
IR_CurFILTER_TIMER_HOURS_MINUTES = 27  # High byte: hours, low byte: minutes
IR_CurFILTER_TIMER_DAYS = 28
IR_TotalWorkingTime_HOURS_MINUTES = 29  # High byte: hours, low byte: minutes
IR_TotalWorkingTime_DAYS = 30
IR_StateFILTER = 31
IR_VerMAIN_FMW_start = 34
IR_VerMAIN_FMW_end = 36
IR_DeviceTYPE = 37
IR_ALARM = 38
IR_StatusBpsRotor = 51
IR_CurSuFanSpeed = 52
IR_CurExFanSpeed = 53