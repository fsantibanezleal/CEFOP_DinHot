#pragma once

#ifndef _BASICCOMPLEX_H_
#define _BASICCOMPLEX_H_

#include <math.h>
#include "BasicFunctions.h"

struct complejo
{
	float real,imaginario;
};

bool 	ExpCompleja(complejo &vRetorno,complejo vValue); // vRetorno = exp(vValue)
bool 	ExpImaginaria(complejo &vRetorno,float vValue); // vRetorno = exp(parteImaginaria)
bool 	ExpImaginariaF(complejo &vRetorno,float vValue,float vFactor);
bool 	ExpImaginariaFR(complejo &vRetorno,float vValue,float vFactor);
bool 	ExpImaginariaV2(complejo *vRetorno,float vValueA,float vValueB);
bool 	ExpImaginariaV3(complejo &vRetorno,float vValueA,float vValueB,float vValueC); // vRetorno = exp(parteImaginaria)
bool 	ExpImaginariaV3R(complejo &vRetorno,float vValueA,float vValueB,float vValueC); // vRetorno = exp(parteImaginaria)
bool	MultCompleja(complejo &vRetorno,complejo vValueA,complejo vValueB); // Multiplicacion de numeros complejos
bool	MultCompleja(complejo &vRetorno,complejo vValueA); // Multiplicacion de numeros complejos
float	ArgumentoComplejo(complejo vValue); // Argumento del complejo...
float	AbsolutoComplejo(complejo vValue); // Magnitud del complejo...

#endif
