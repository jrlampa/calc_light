import math
from typing import List

from .models import CalculationInput, CalculationResult, Conductor

def calculate_level_resultant(inputs: List[CalculationInput], conductors: List[Conductor]) -> CalculationResult:
    """
    Implements Excel formulas for calculating wind force, tracion, components and resultant forces.
    Reference: CÁLCULO DE TRAÇÃO OII-25-2249.xlsm (Ponto (1) sheet)
    """
    total_wind_x = 0.0
    total_wind_y = 0.0
    total_comp_x = 0.0
    total_comp_y = 0.0
    
    total_diameter = 0.0
    total_weight = 0.0

    for calc_input, conductor in zip(inputs, conductors):
        # Diâmetro Total: =IF(C12>0,C21*C20+C23," ")
        diam_total = conductor.cable_qty * conductor.diameter_m + conductor.messenger_diameter
        
        # Peso Total: =IF(C12>0,C19*C21+C22," ")
        weight_total = conductor.weight_kg_m * conductor.cable_qty + conductor.messenger_weight

        # Força do vento nos condutores - X: =ROUND(C26*C14/2*C24*COS(PI()/180*C16),2)
        wind_x = round(calc_input.wind_pressure * calc_input.span_m / 2 * diam_total * math.cos(math.radians(calc_input.angle_deg)), 2)
        
        # Força do vento nos condutores - Y: =ROUND(C26*C14/2*C24*SIN(PI()/180*C16),2)
        wind_y = round(calc_input.wind_pressure * calc_input.span_m / 2 * diam_total * math.sin(math.radians(calc_input.angle_deg)), 2)

        # Tração dos condutores: =(C25*C14^2)/(8*C15)
        traction = (weight_total * calc_input.span_m**2) / (8 * calc_input.sag_m) if calc_input.sag_m > 0 else 0.0

        # Compx: =ROUND(C29*COS(PI()/180*C16),2)
        comp_x = round(traction * math.cos(math.radians(calc_input.angle_deg)), 2)
        
        # Compy: =ROUND(C29*SIN(PI()/180*C16),2)
        comp_y = round(traction * math.sin(math.radians(calc_input.angle_deg)), 2)
        
        total_wind_x += wind_x
        total_wind_y += wind_y
        total_comp_x += comp_x
        total_comp_y += comp_y
        total_diameter += diam_total
        total_weight += weight_total
        
    # Resultante: =SQRT(SUM(C30:L30)^2+SUM(C31:L31)^2)+SQRT(SUM(C27:L27)^2+SUM(C28:L28)^2)
    resultant = math.sqrt(total_comp_x**2 + total_comp_y**2) + math.sqrt(total_wind_x**2 + total_wind_y**2)

    # Angle: =IF(SUM(C30:L30)=0,ROUNDUP(ATAN(SUM(C31:L31)/1)*180/PI(),0),IF(SUM(C30:L30)<0,ATAN(SUM(C31:L31)/SUM(C30:L30))*180/PI()+180,ATAN(SUM(C31:L31)/SUM(C30:L30))*180/PI()))
    if total_comp_x == 0:
        if total_comp_y == 0:
            angle = 0.0
        else:
            angle = math.ceil(math.degrees(math.atan(total_comp_y)))
    elif total_comp_x < 0:
        angle = math.degrees(math.atan(total_comp_y / total_comp_x)) + 180
    else:
        angle = math.degrees(math.atan(total_comp_y / total_comp_x))

    # Lever arm adjusted traction on pole
    # Formula: Resultant * Anchorage_Height / (Pole_Height * 0.9 - 0.6 - 0.1)
    traction_on_pole = 0.0
    if inputs and resultant > 0:
        pole_h = inputs[0].pole_height_m
        anch_h = inputs[0].anchorage_height_m
        if pole_h > 0:
            denominator = (pole_h * 0.9) - 0.6 - 0.1
            if denominator > 0:
                traction_on_pole = resultant * anch_h / denominator

    return CalculationResult(
        total_diameter_m=round(total_diameter, 4),
        total_weight_kg_m=round(total_weight, 4),
        wind_force_x=total_wind_x,
        wind_force_y=total_wind_y,
        traction_dan=round(traction, 2), # traction from last calc basically, or total?
        comp_x=total_comp_x,
        comp_y=total_comp_y,
        resultant_level_dan=round(resultant, 2),
        resultant_angle_deg=round(angle, 2),
        traction_on_pole_dan=round(traction_on_pole, 2)
    )
