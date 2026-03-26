#pragma once

#ifndef _MATDINHOT_H_
#define _MATDINHOT_H_

#include "BasicFunctions.h"

using namespace std;

#define OPENANGLE		0.0f
#define FACTORESPACIO	(1.0f/1000000.0f)

class MatDinHot
{
private:
	bool		_busy,_reArmar;
	unsigned	_resMaskX,_resMaskY,_resPantallaX,_resPantallaY; // resolucion de la mascara
	unsigned	_numTrampas; // numero de trampas
	int			_selectedtrampa;
	float		_maximo,_xI,_xN,_tolerancia,_factorTolerancia; // tolerancia
	float		_distFocal,_lambda, _vectorOnda; // distancia focal f... longitud de onda
	float		*_alfaTrampa,*_intensidadTrampa,**_phi,**_coordX,**_coordY,**_coordXCuadrado,**_coordYCuadrado; //alfa ... pesos de las trampas matrices de cordenadas
	float		***_rrho; // Seudo representacion del producto punto .
	stVertex	*_posicionTrampa;
	complejo	**intermedioCampo,**_phiFull;
public:
	MatDinHot();
	~MatDinHot();

	void		FactorAmplitudCampoElectricoConstante(void);
	void		AmplitudCampoElectrico(complejo &vRetorno, unsigned vIndiceTrampa);
	complejo	AmplitudCampoElectrico(unsigned vIndiceTrampa);
	bool		CalcResultPhi(complejo **vMatRetorno,float vFactor,unsigned vIndiceTrampa);
	bool		CalcAnguloPhi(void);
	void		InitPhiFull(void);
	void		RandomizePhi(void);
	void		CalcMatriz(void);

	unsigned	GetNumTrampas(void){return _numTrampas;};
	void		SetNumTrampas(unsigned vValue){_numTrampas = vValue;};
	unsigned	GetResX(void){return _resMaskX;};
	unsigned	GetResY(void){return _resMaskY;};
	float**		GetPhi(void){return _phi;};
	stVertex*	GetPosTrampas(void){return _posicionTrampa;};
	void		SetPosTrampas(stVertex* vValue)
				{
					register unsigned i;
					for(i=0;i<_numTrampas;i++)
					{
						_posicionTrampa[i] = vValue[i];
					}
				};

	void		SetResPantalla(unsigned vX,unsigned vY){_resPantallaX = vX;_resPantallaY = vY;};
	void		AddTrampa(float vX,float vY);
	void		DeleteTrampa(float vX,float vY);
	void		SelectMove(float vX,float vY);
	void		Move(float vX,float vY);
	void		FreeMove(void);
};

#endif
