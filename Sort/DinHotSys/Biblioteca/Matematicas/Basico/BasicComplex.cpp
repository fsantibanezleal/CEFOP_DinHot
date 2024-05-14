#include "BasicComplex.h"

bool 	ExpCompleja(complejo &vRetorno,complejo vValue)
{
	register float temp = exp(vValue.real);
	ExpImaginaria(vRetorno,vValue.imaginario);
	vRetorno.real *= temp;
	vRetorno.imaginario *= temp;
	return true;
}; // vRetorno = exp(vValue)

bool 	ExpImaginaria(complejo &vRetorno,float vValue)
{
	vRetorno.real = cos(vValue);
	vRetorno.imaginario= sin(vValue);
	//vRetorno.imaginario = sqrtf(1.0f - vRetorno.real*vRetorno.real);
	return true;
}; // vRetorno = exp(parteImaginaria)

bool 	ExpImaginariaF(complejo &vRetorno,float vValue,float vFactor)
{
	//register float coseno = cos(vValue);
	vRetorno.real = vFactor*cos(vValue);
	vRetorno.imaginario= vFactor*sin(vValue);
	//vRetorno.imaginario = vFactor*sqrtf(1.0f - coseno*coseno);
	return true;
}; // vRetorno = exp(parteImaginaria)

bool 	ExpImaginariaFR(complejo &vRetorno,float vValue,float vFactor)
{
	//register float coseno = cos(vValue);
	vRetorno.real		+= vFactor*cos(vValue);
	vRetorno.imaginario	+= vFactor*sin(vValue);
	//vRetorno.imaginario = vFactor*sqrtf(1.0f - coseno*coseno);
	return true;
}; // vRetorno = exp(parteImaginaria)

bool 	ExpImaginariaV2(complejo *vRetorno,float vValueA,float vValueB)
{
	complejo temp;
	ExpImaginaria(temp,vValueA + vValueB);
	vRetorno->real = temp.real;
	vRetorno->imaginario = temp.imaginario;
	return true;
};// vRetorno = exp(parteImaginaria)

bool 	ExpImaginariaV3(complejo &vRetorno,float vValueA,float vValueB,float vValueC)
{
	ExpImaginaria(vRetorno,vValueA + vValueB + vValueC);
	
	return true;
};// vRetorno = exp(parteImaginaria)


bool 	ExpImaginariaV3R(complejo &vRetorno,float vValueA,float vValueB,float vValueC)
{
	complejo temp;

	ExpImaginaria(temp,vValueA + vValueB + vValueC);	
	vRetorno.real		+= temp.real;
	vRetorno.imaginario += temp.imaginario;
	return true;
};// vRetorno = exp(parteImaginaria)

bool	MultCompleja(complejo &vRetorno,complejo vValueA,complejo vValueB)
{
	vRetorno.real = vValueA.real*vValueB.real - vValueA.imaginario*vValueB.imaginario;
	vRetorno.imaginario = vValueA.real*vValueB.imaginario + vValueA.imaginario*vValueB.real;
	return true;
};


bool	MultCompleja(complejo &vRetorno,complejo vValue)
{
	return MultCompleja(vRetorno,vRetorno,vValue);
};

float	ArgumentoComplejo(complejo vValue)
{
	return atan2(vValue.imaginario, vValue.real);
};

float	AbsolutoComplejo(complejo vValue)
{
	return sqrtf(vValue.real*vValue.real + vValue.imaginario*vValue.imaginario);
};
