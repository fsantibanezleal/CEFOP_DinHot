#include "MatDinHot.h"
#include <math.h>

MatDinHot::MatDinHot()
{
	register unsigned i,j,k;

	_reArmar = true;
	_selectedtrampa = -1;
	_busy = false;
	_xI = 0;
	_xN = 5;

	_resMaskX = 1280;
	_resMaskY = 1024;
	_numTrampas = 4;
	_tolerancia = 0.000000001f;
	_factorTolerancia = 0.5f;

	_coordX = new float*[_resMaskX];
	_coordY = new float*[_resMaskX];

	_coordXCuadrado = new float*[_resMaskX];
	_coordYCuadrado = new float*[_resMaskX];

	_phi		= new float*[_resMaskX];
	_phiFull	= new complejo*[_resMaskX];
	for(i = 0; i < _resMaskX; i++)
	{
		_coordX[i] = new float[_resMaskY];
		_coordY[i] = new float[_resMaskY];

		_coordXCuadrado[i] = new float[_resMaskY];
		_coordYCuadrado[i] = new float[_resMaskY];

		_phi[i]		= new float[_resMaskY];
		_phiFull[i]	= new complejo[_resMaskY];
		for(j = 0; j < _resMaskY; j++)
		{
			_coordX[i][j] = (float)(i + 1);
			_coordY[i][j] = (float)(j + 1);

			_coordXCuadrado[i][j] = (float)(i + 1)*(i + 1);
			_coordYCuadrado[i][j] = (float)(j + 1)*(j + 1);

			_phi[i][j]  = 0.0f; // hacer random,,,,
			_phiFull[i][j].real = _phiFull[i][j].imaginario = 0.0f;
		}
	}

	_distFocal	= 0.0000005f;
	_lambda		= 632;
	_vectorOnda = 2 * PI / _lambda;

	_alfaTrampa			= new float[10];
	_intensidadTrampa	= new float[10];
	_posicionTrampa		= new stVertex[10];

	SetFull(_posicionTrampa[0],FACTORESPACIO*100.0f,FACTORESPACIO*100.0f,0.0f);
	SetFull(_posicionTrampa[1],-FACTORESPACIO*100.0f,FACTORESPACIO*100.0f,0.0f);
	SetFull(_posicionTrampa[2],FACTORESPACIO*100.0f,-FACTORESPACIO*100.0f,0.0f);
	SetFull(_posicionTrampa[3],-FACTORESPACIO*100.0f,-FACTORESPACIO*100.0f,0.0f);

	_rrho	= new float**[10];
	for(i = 0; i < _numTrampas; i++)
	{
		_alfaTrampa[i] = sqrt(1.0f);
		_intensidadTrampa[i] = fabs(_alfaTrampa[i]) * fabs(	_alfaTrampa[i]);

		_rrho[i] = new float*[_resMaskX];
		for(j = 0; j < _resMaskX; j++)
		{
			_rrho[i][j] = new float[_resMaskY];

			for(k = 0; k < _resMaskY; k++)
			{
				_rrho[i][j][k] = _posicionTrampa[i].x * _coordX[j][k] + _posicionTrampa[i].y * _coordY[j][k];
			}
		}
	}
};

MatDinHot::~MatDinHot()
{

};

void MatDinHot::FactorAmplitudCampoElectricoConstante(void)
{
	register unsigned i,j,k;
	for(i = 0; i < _numTrampas; i++)
	{
		for(j = 0; j < _resMaskX; j++)
		{
			for(k = 0; k < _resMaskY; k++)
			{

			}
		}
	}
	
};

void MatDinHot::AmplitudCampoElectrico(complejo &vRetorno, unsigned vIndiceTrampa)
{
	register unsigned i,j;

	complejo		temp;
	register float	imaginario1[3],imaginario2[3],imaginario3[3],imaginario4[3],factor;
	
	vRetorno.real = vRetorno.imaginario = 0.0f;

	register unsigned limites[5],cuarto = _resMaskY / 4;
	limites[0] = 0;
	limites[1] = cuarto;
	limites[2] = 2 * cuarto;
	limites[3] = 3 * cuarto;
	limites[4] = _resMaskY;
	

	for(i = 0; i < _resMaskX; i++)
	{
		#pragma omp parallel sections //num_threads(4)
		{
			#pragma omp section
			{
				for(j = limites[0]; j < limites[1]; j++)
				{
					imaginario1[0] = _phi[i][j];
					imaginario1[1] = -(_distFocal / _vectorOnda)*_rrho[vIndiceTrampa][i][j];
					imaginario1[2] = (_distFocal / (_vectorOnda*_vectorOnda))* (_coordXCuadrado[i][j] + _coordYCuadrado[i][j])*_posicionTrampa[vIndiceTrampa].z;

					ExpImaginaria(temp,imaginario1[0]+imaginario1[1]+imaginario1[2]);
					vRetorno.real		+= temp.real;
					vRetorno.imaginario	+= temp.imaginario;
				}
			}
			#pragma omp section
			{
				for(j = limites[1]; j < limites[2]; j++)
				{
					imaginario2[0] = _phi[i][j];
					imaginario2[1] = -(_distFocal / _vectorOnda)*_rrho[vIndiceTrampa][i][j];
					imaginario2[2] = (_distFocal / (_vectorOnda*_vectorOnda))* (_coordXCuadrado[i][j] + _coordYCuadrado[i][j])*_posicionTrampa[vIndiceTrampa].z;

					ExpImaginaria(temp,imaginario2[0]+imaginario2[1]+imaginario2[2]);
					vRetorno.real		+= temp.real;
					vRetorno.imaginario	+= temp.imaginario;
				}
			}
			#pragma omp section
			{
				for(j = limites[2]; j < limites[3]; j++)
				{
					imaginario3[0] = _phi[i][j];
					imaginario3[1] = -(_distFocal / _vectorOnda)*_rrho[vIndiceTrampa][i][j];
					imaginario3[2] = (_distFocal / (_vectorOnda*_vectorOnda))* (_coordXCuadrado[i][j] + _coordYCuadrado[i][j])*_posicionTrampa[vIndiceTrampa].z;

					ExpImaginaria(temp,imaginario3[0]+imaginario3[1]+imaginario3[2]);
					vRetorno.real		+= temp.real;
					vRetorno.imaginario	+= temp.imaginario;
				}
			}
			#pragma omp section
			{
				for(j = limites[3]; j < limites[4]; j++)
				{
					imaginario4[0] = _phi[i][j];
					imaginario4[1] = -(_distFocal / _vectorOnda)*_rrho[vIndiceTrampa][i][j];
					imaginario4[2] = (_distFocal / (_vectorOnda*_vectorOnda))* (_coordXCuadrado[i][j] + _coordYCuadrado[i][j])*_posicionTrampa[vIndiceTrampa].z;

					ExpImaginaria(temp,imaginario4[0]+imaginario4[1]+imaginario4[2]);
					vRetorno.real		+= temp.real;
					vRetorno.imaginario	+= temp.imaginario;
				}
			}
		}
	}

	factor = 1.0f / (float)(_resMaskX * _resMaskY);

	vRetorno.real		*= factor;
	vRetorno.imaginario	*= factor;
};

complejo MatDinHot::AmplitudCampoElectrico(unsigned vIndiceTrampa)
{
	register unsigned i,j;

	complejo		sumatoria,temp;
	register float	imaginario[3],factor;
	
	sumatoria.real = sumatoria.imaginario = 0.0f;

	for(i = 0; i < _resMaskX; i++)
	{
		for(j = 0; j < _resMaskY; j++)
		{
			imaginario[0] = _phi[i][j];
			imaginario[1] = -(_vectorOnda / _distFocal)*_rrho[vIndiceTrampa][i][j];
			imaginario[2] = (_vectorOnda / (_distFocal*_distFocal))* (_coordXCuadrado[i][j] + _coordYCuadrado[i][j])*_posicionTrampa[vIndiceTrampa].z;

			ExpImaginaria(temp,imaginario[0]+imaginario[1]+imaginario[2]);
			sumatoria.real			+= temp.real;
			sumatoria.imaginario	+= temp.imaginario;
		}
	}

	factor = 1.0f / (float)(_resMaskX * _resMaskY);

	sumatoria.real			*= factor;
	sumatoria.imaginario	*= factor;

	return sumatoria;
};

bool MatDinHot::CalcResultPhi(complejo **vMatRetorno,float vFactor,unsigned vIndiceTrampa)
{
	register unsigned i,j;

	register float imaginario[2];
	complejo temp;

	for(i = 0; i < _resMaskX; i++)
	{
		for(j = 0; j < _resMaskY; j++)
		{
			imaginario[0] = (_vectorOnda / _distFocal)*_rrho[vIndiceTrampa][i][j];
			imaginario[1] = -(_vectorOnda / (_distFocal*_distFocal))* (_coordXCuadrado[i][j] + _coordYCuadrado[i][j])*_posicionTrampa[vIndiceTrampa].z;
			
			ExpImaginariaF(temp,imaginario[0]+imaginario[1],vFactor);
			vMatRetorno[i][j].real += temp.real;
			vMatRetorno[i][j].imaginario += temp.imaginario;
		}
	}
	return true;
};

bool MatDinHot::CalcAnguloPhi(void)
{
	register unsigned i,j;
	register float temporal;

	_maximo = 0.0f;
	for(i = 0; i < _resMaskX; i++)
	{
		for(j = 0; j < _resMaskY; j++)
		{
			temporal = ArgumentoComplejo(_phiFull[i][j]);
			_phi[i][j] = temporal;
			if(temporal > _maximo)
			{
				_maximo = temporal;
			}
		}
	}
	return true;
};

void MatDinHot::InitPhiFull(void)
{
	register unsigned i,j;
	for(i = 0; i < _resMaskX; i++)
	{
		for(j = 0; j < _resMaskY; j++)
		{
			_phiFull[i][j].real = _phiFull[i][j].imaginario = 0.0f;
		}
	}
};

void MatDinHot::RandomizePhi(void)
{
	register unsigned i,j;
	for(i = 0; i < _resMaskX; i++)
	{
		for(j = 0; j < _resMaskY; j++)
		{
			_phiFull[i][j].real = _phiFull[i][j].imaginario = 0.0f;
			_phi[i][j] = (float)rand()/(float)RAND_MAX;
		}
	}
};

void MatDinHot::CalcMatriz(void)
{
	if(!_busy && _reArmar)
	{
		// Iniciar secuencia .. hacer phi random...
		//InitPhiFull();
		RandomizePhi();

		register unsigned i,j;
		register float xI0,xICiclo,xN;
		float		*intensidadN,*alfaN;
		complejo	*epsN;

		alfaN		= new float[_numTrampas];
		intensidadN	= new float[_numTrampas];
		epsN		= new complejo[_numTrampas];

		xICiclo = _xI;
		xN = _xN;
		while(xN >= _tolerancia)
		{
			xI0 = xICiclo;
			for(i = 0; i < _numTrampas; i++)
			{
				AmplitudCampoElectrico(epsN[i],i);
				alfaN[i]		= AbsolutoComplejo(epsN[i]);
				intensidadN[i]	= alfaN[i] * alfaN[i];
				xICiclo			+= (_intensidadTrampa[i] - intensidadN[i])*(_intensidadTrampa[i] - intensidadN[i]);

				alfaN[i]		= ((1.0f  - _tolerancia) + _tolerancia * (_alfaTrampa[i]/alfaN[i]))*_alfaTrampa[i]; // Paso iterativo.. verificar

				CalcResultPhi(_phiFull,alfaN[i],i);
			}
			CalcAnguloPhi();
			xICiclo = sqrt(xICiclo /(_numTrampas * _numTrampas));
			xN = (xICiclo - xI0) / xICiclo;
		}
		// Phi contiene la matriz a renderizar
		_reArmar = false;
		for(i = 0; i < _resMaskX; i++)
		{
			for(j = 0; j < _resMaskY; j++)
			{
				_phi[i][j] = _phi[i][j]/ _maximo;
			}
		}
	}
};

void MatDinHot::AddTrampa(float vX,float vY)
{
	register unsigned j,k;
	_busy = true;

	_posicionTrampa[_numTrampas].x = (vX -  0.5f*_resPantallaX)*(400.0f/_resPantallaX)*FACTORESPACIO;
	_posicionTrampa[_numTrampas].y = ((_resPantallaY - vY) -  0.5f*_resPantallaY)*(400.0f/_resPantallaY)*FACTORESPACIO;
	_posicionTrampa[_numTrampas].z = 0.0f;

		_alfaTrampa[_numTrampas] = sqrt(1.0f);
		_intensidadTrampa[_numTrampas] = fabs(_alfaTrampa[_numTrampas]) * fabs(	_alfaTrampa[_numTrampas]);

		_rrho[_numTrampas] = new float*[_resMaskX];
		for(j = 0; j < _resMaskX; j++)
		{
			_rrho[_numTrampas][j] = new float[_resMaskY];

			for(k = 0; k < _resMaskY; k++)
			{
				_rrho[_numTrampas][j][k] = _posicionTrampa[_numTrampas].x * _coordX[j][k] + _posicionTrampa[_numTrampas].y * _coordY[j][k];
			}
		}
	_numTrampas++;
	_reArmar = true;
	_busy = false;
};
void MatDinHot::DeleteTrampa(float vX,float vY)
{
	_busy = true;
};

void MatDinHot::SelectMove(float vX,float vY)
{
	register unsigned i;
	stVertex posReq,temp;
	
	posReq.x = (vX -  0.5f*_resPantallaX)*(400.0f/_resPantallaX)*FACTORESPACIO;
	posReq.y = ((_resPantallaY - vY) -  0.5f*_resPantallaY)*(400.0f/_resPantallaY)*FACTORESPACIO;
	posReq.z = 0.0f;

	float distancia;
	for(i = 0; i < _numTrampas; i++)
	{
		distancia = DireccionByResta(temp,posReq,_posicionTrampa[i]);
		if(fabs(distancia)<= 5.0f *FACTORESPACIO)
		{
			_selectedtrampa = i;
			i = 100;
		}
	}
};

void MatDinHot::Move(float vX,float vY)
{
	_busy = true;
	register unsigned j,k;
	if(_selectedtrampa> -1)
	{
		_posicionTrampa[_selectedtrampa].x = (vX -  0.5f*_resPantallaX)*(400.0f/_resPantallaX)*FACTORESPACIO;
		_posicionTrampa[_selectedtrampa].y = ((_resPantallaY - vY) -  0.5f*_resPantallaY)*(400.0f/_resPantallaY)*FACTORESPACIO;

		for(j = 0; j < _resMaskX; j++)
		{
			for(k = 0; k < _resMaskY; k++)
			{
				_rrho[_selectedtrampa][j][k] = _posicionTrampa[_selectedtrampa].x * _coordX[j][k] + _posicionTrampa[_selectedtrampa].y * _coordY[j][k];
			}
		}
	}
	_busy = false;
	//_reArmar = true;
};

void MatDinHot::FreeMove(void)
{
	_selectedtrampa = -1;
	_busy = false;
	_reArmar = true;
};