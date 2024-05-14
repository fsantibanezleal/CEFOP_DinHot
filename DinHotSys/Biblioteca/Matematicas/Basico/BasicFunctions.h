#pragma once

#ifndef _BASICSTRUCTURES_H_
#define _BASICSTRUCTURES_H_

#include "BasicStructures.h"
#include "BasicComplex.h"

#define OPENANGLE 0.0f
#define SMALLESTVALUE 0.000001f
#define BIGGESTVALUE 100000.0f

#define POINT_IN_TRI(V0,U0,U1,U2)           \
{                                           \
	float a,b,c,d0,d1,d2;                   \
	/* is T1 completly inside T2? */        \
	/* check if V0 is inside tri(U0,U1,U2) */\
	a=U1[i1]-U0[i1];                        \
	b=-(U1[i0]-U0[i0]);                     \
	c=-a*U0[i0]-b*U0[i1];                   \
	d0=a*V0[i0]+b*V0[i1]+c;                 \
											\
	a=U2[i1]-U1[i1];                        \
	b=-(U2[i0]-U1[i0]);                     \
	c=-a*U1[i0]-b*U1[i1];                   \
	d1=a*V0[i0]+b*V0[i1]+c;                 \
											\
	if(d0*d1>0.0)                           \
	{										\
		a=U0[i1]-U2[i1];                    \
		b=-(U0[i0]-U2[i0]);                 \
		c=-a*U2[i0]-b*U2[i1];               \
		d2=a*V0[i0]+b*V0[i1]+c;             \
											\
		if(d0*d2>0.0) return true;          \
	}                                       \
}

bool 	IsSmall(float vValue);
bool 	IsBig(float vValue);

bool	IsInfinite(stVertex vRetorno);
bool	IsZero(stVertex vRetorno);

float	LengthVector(stVertex V);
void	Igualar(float *vRetorno,float *vValue);
void	Igualar(float *vRetorno,stVertex vValue);
void	Igualar(stVertex &vRetorno,float *vValue);
void	MultiplicarMatrizR(float *C, float *A, float *B);
void	MultiplicarMatrizVectorR(float *C, float *A, float *B);
void	MultiplicarMatrizVectorR(stVertex &C, float *A, stVertex B);
void	SetTraslacion(float *m,float vTx,float vTy,float vTz);
void	SetInvTraslacion(float *m,float vTx,float vTy,float vTz);
void	SetTraslacion(float *m,stVertex vTras);
void	SetInvTraslacion(float *m,stVertex vTras);
void	SetRotacion(float *m,float vAngulo, stVertex vDireccion);
void	SetInvRotacion(float *m,float vAngulo, stVertex vDireccion);
void	SetRotacionCos(float *m,float vCosAngulo, stVertex vDireccion);
void	SetInvRotacionCos(float *m,float vCosAngulo, stVertex vDireccion);

bool	InversaLU(float *vRetorno, float *vMatriz);

void 	Zero(stVertex &vValue);
void 	Infinite(stVertex &vValue);
void 	SetEqual(stVertex &vValue,float vChange);
void 	SetFull(stVertex &vValue,float vChangeX,float vChangeY,float vChangeZ);
void 	Limpiar(stVertex &vValue);
void 	Igualar(stVertex &vValue,stVertex v2);
void 	Amplificar(stVertex &vValue ,float vAlfa );
void 	Amplificar(stVertex &vValue,stVertex v2 ,float vAlfa );
void 	Amplificar(stVertex &vValue,float vAlfa,stVertex v2  );
void 	Suma(stVertex &vValue ,stVertex v1, stVertex v2 );
void 	Resta(stVertex &vValue ,stVertex v1, stVertex v2 );
void	MultiplicacionPuntual(stVertex &vValue ,stVertex v1, stVertex v2);

stVertex	Resta(stVertex v1, stVertex v2 );
stVertex	Suma(stVertex v1, stVertex v2 );

float 	Distancia(stVertex v1 ,stVertex v2);
float	NormalizeR(stVertex &vValue);
void 	Cross(stVertex &vValue ,stVertex v1, stVertex v2);
float	CrossNormalize(stVertex &vValue ,stVertex v1, stVertex v2);
float 	Dot(stVertex v1 ,stVertex v2);
float 	DireccionByResta(stVertex &vPRayo ,stVertex vFin,stVertex vInicio);
bool	Perpendicular(stVertex &vPerpendicular, stVertex vVector);

void 	Ray(stVertex &vPRayo ,stVertex vInicio,stVertex vDireccion, float vAlfa);
void 	Ray(stVertex &vPRayo ,stVertex vInicio,float vAlfa,stVertex vDireccion);

float 	DistanciaAPlano(stVertex vNormalT , stVertex vDirMov, stVertex vPuntoPlano,stVertex vPuntoInteres);
float 	DistanciaAPlanoN(stVertex vNormalT , stVertex vPuntoPlano,stVertex vPuntoInteres);

bool 	IsPointInTriangle(stVertex vNormal,stVertex vPunto,stVertex vTriangulo[3]);
bool	IsPointInTriangleS(stVertex vNormal,stVertex vPunto,stVertex vTriangulo[3]);
bool	IsPointInTriangleN(stVertex vNormal,stVertex vPunto,stVertex vTriangulo[3]);
bool	IsPointInTriangleA(stVertex vNormal,stVertex vPunto,stVertex vTriangulo[3],int vTipoAnalisis);
bool	IsPointInTriangleB(stVertex vNormal,stVertex vPunto,stVertex vTriangulo[3]);
void	OrdenarValoresMinMax(float* vValue,unsigned vDimension);

int		InterseccionRayoEsfera(float *vAlfas, stVertex vOrigen, stVertex vDireccion, stVertex vCentro, float vRadio);
bool	InterseccionClosedRayoEsfera(float *vAlfa, stVertex vOrigen, stVertex vDireccion, stVertex vCentro, float vRadio);
bool	InterseccionFarestRayoEsfera(float *vAlfa, stVertex vOrigen, stVertex vDireccion, stVertex vCentro, float vRadio);

#endif
