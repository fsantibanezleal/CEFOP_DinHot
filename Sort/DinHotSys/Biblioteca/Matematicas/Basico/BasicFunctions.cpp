#include "BasicFunctions.h"

bool IsSmall(float vValue)
{
	return (fabs(vValue) <= SMALLESTVALUE)? true:false;
};

bool IsBig(float vValue)
{
	return (fabs(vValue) >= BIGGESTVALUE)? true:false;
};

bool IsInfinite(stVertex vRetorno)
{
	return (vRetorno.x == BIGGESTVALUE)? true: false;
};

bool IsZero(stVertex vRetorno)
{
	return IsSmall(LengthVector(vRetorno));
};

float LengthVector(stVertex V)
{
	return sqrt(V.x*V.x + V.y*V.y + V.z*V.z);
};

void Igualar(float *vRetorno,float *vValue)
{
	register unsigned i;
	for(i = 0; i < 16; i++)
	{
		vRetorno[i] = vValue[i];
	}
};

void Igualar(float *vRetorno,stVertex vValue)
{
	vRetorno[0] = vValue.x;
	vRetorno[1] = vValue.y;
	vRetorno[2] = vValue.z;
	vRetorno[3] = 1.0f;
};

void Igualar(stVertex &vRetorno,float *vValue)
{
	vRetorno.x = vValue[0];
	vRetorno.y = vValue[1];
	vRetorno.z = vValue[2];
};

void MultiplicarMatrizR(float *C, float *A, float *B)
{
	register float sum,tempA[16],tempB[16];
	register int i,j,k;

	Igualar(tempA,A);
	Igualar(tempB,B); // Es mas rapido hacer un solo for aqui... :D .. en fin esto se hace solo en cada actualizacion.. hay time
	for( i = 0 ; i < 4 ; i++)
	{
		for( j = 0 ; j < 4 ; j++)
		{
			sum = 0.0f;
			for( k = 0 ; k < 4 ; k++)
			{
				sum += tempA[ k * 4 + i] * tempB[ j * 4 + k];
			}
			C[ j * 4 + i] = sum;
		}
	}

};

void MultiplicarMatrizVectorR(float *C, float *A, float *B)
{
	register int i,j;
	register float sum,tempB[4];

	Igualar(tempB,B);
	for( i = 0 ; i < 4 ; i++)
	{
		sum = 0.0f;
		for(j = 0 ; j < 4 ; j++)
		{
			sum += A[ j*4 + i] * tempB[j];
		}
		C[i] = sum;
	}
};

void MultiplicarMatrizVectorR(stVertex &C, float *A, stVertex B)
{
	register int i,j;
	register float sum,tempB[4],tempRet[4];

	Igualar(tempB,B);
	for( i = 0 ; i < 4 ; i++)
	{
		sum = 0.0f;
		for(j = 0 ; j < 4 ; j++)
		{
			sum += A[ j*4 + i] * tempB[j];
		}
		tempRet[i] = sum;
	}
	Igualar(C,tempRet);
};

void SetTraslacion(float *m,float vTx,float vTy,float vTz)
{
	m[0]=1.0f;m[4]=0.0f;m[8 ]=0.0f;m[12]=vTx;
	m[1]=0.0f;m[5]=1.0f;m[9 ]=0.0f;m[13]=vTy;
	m[2]=0.0f;m[6]=0.0f;m[10]=1.0f;m[14]=vTz;
	m[3]=0.0f;m[7]=0.0f;m[11]=0.0f;m[15]=1.0f;
};

void SetInvTraslacion(float *m,float vTx,float vTy,float vTz)
{
	m[0]=1.0f;m[4]=0.0f;m[8 ]=0.0f;m[12]=-vTx;
	m[1]=0.0f;m[5]=1.0f;m[9 ]=0.0f;m[13]=-vTy;
	m[2]=0.0f;m[6]=0.0f;m[10]=1.0f;m[14]=-vTz;
	m[3]=0.0f;m[7]=0.0f;m[11]=0.0f;m[15]=1.0f;
};

void SetTraslacion(float *m,stVertex vTras)
{
	m[0]=1.0f;m[4]=0.0f;m[8 ]=0.0f;m[12]=vTras.x;
	m[1]=0.0f;m[5]=1.0f;m[9 ]=0.0f;m[13]=vTras.y;
	m[2]=0.0f;m[6]=0.0f;m[10]=1.0f;m[14]=vTras.z;
	m[3]=0.0f;m[7]=0.0f;m[11]=0.0f;m[15]=1.0f;
};

void SetInvTraslacion(float *m,stVertex vTras)
{
	m[0]=1.0f;m[4]=0.0f;m[8 ]=0.0f;m[12]=-vTras.x;
	m[1]=0.0f;m[5]=1.0f;m[9 ]=0.0f;m[13]=-vTras.y;
	m[2]=0.0f;m[6]=0.0f;m[10]=1.0f;m[14]=-vTras.z;
	m[3]=0.0f;m[7]=0.0f;m[11]=0.0f;m[15]=1.0f;
};

void SetRotacion(float *m,float vAngulo, stVertex vDireccion)
{
	register float unoMenosCos,sinAlfa,cosAlfa;
	stVertex dir,dir2;
	Igualar(dir,vDireccion);
	MultiplicacionPuntual(dir2,dir,dir);

	NormalizeR(vDireccion);

	cosAlfa		= cos(vAngulo);
	sinAlfa		= sin(vAngulo);
	unoMenosCos = 1.0f - cosAlfa;

	m[0]=(dir2.x + (dir2.y + dir2.z)* cosAlfa);		m[4]=(dir.x*dir.y*unoMenosCos - dir.z*sinAlfa);	m[8 ]=(dir.x*dir.z*unoMenosCos + dir.y*sinAlfa);	m[12]=0.0f;
	m[1]=(dir.x*dir.y*unoMenosCos + dir.z*sinAlfa);	m[5]=(dir2.y + (dir2.x + dir2.z)* cosAlfa);		m[9 ]=(dir.y*dir.z*unoMenosCos - dir.x*sinAlfa);	m[13]=0.0f;
	m[2]=(dir.x*dir.z*unoMenosCos - dir.y*sinAlfa);	m[6]=(dir.y*dir.z*unoMenosCos + dir.x*sinAlfa);	m[10]=(dir2.z + (dir2.x + dir2.y)* cosAlfa);		m[14]=0.0f;
	m[3]=0.0f;										m[7]=0.0f;										m[11]=0.0f;											m[15]=1.0f;
};

void SetInvRotacion(float *m,float vAngulo, stVertex vDireccion)
{
	vAngulo = - vAngulo;
	SetRotacion(m,vAngulo,vDireccion);
};

void SetRotacionCos(float *m,float vCosAngulo, stVertex vDireccion)
{
	register float unoMenosCos,sinAlfa;
	stVertex dir,dir2;
	Igualar(dir,vDireccion);
	MultiplicacionPuntual(dir2,dir,dir);

	NormalizeR(vDireccion);

	unoMenosCos = 1.0f - vCosAngulo;
	sinAlfa = sqrtf(1.0f - vCosAngulo*vCosAngulo);

	m[0]=(dir2.x + (dir2.y + dir2.z)* vCosAngulo);	m[4]=(dir.x*dir.y*unoMenosCos - dir.z*sinAlfa);	m[8 ]=(dir.x*dir.z*unoMenosCos + dir.y*sinAlfa);	m[12]=0.0f;
	m[1]=(dir.x*dir.y*unoMenosCos + dir.z*sinAlfa);	m[5]=(dir2.y + (dir2.x + dir2.z)* vCosAngulo);	m[9 ]=(dir.y*dir.z*unoMenosCos - dir.x*sinAlfa);	m[13]=0.0f;
	m[2]=(dir.x*dir.z*unoMenosCos - dir.y*sinAlfa);	m[6]=(dir.y*dir.z*unoMenosCos + dir.x*sinAlfa);	m[10]=(dir2.z + (dir2.x + dir2.y)* vCosAngulo);		m[14]=0.0f;
	m[3]=0.0f;										m[7]=0.0f;										m[11]=0.0f;											m[15]=1.0f;
};

void SetInvRotacionCos(float *m,float vCosAngulo, stVertex vDireccion)
{
	vCosAngulo = - vCosAngulo;
	SetRotacionCos(m,vCosAngulo,vDireccion);
};

bool InversaLU(float *vRetorno, float *vMatriz)
{
	int filas,columnas;
	filas=columnas=4;

	int i,j,k;
	float m_origen_copy[16];
	float* b = new float[columnas];
	float factor,sum;
	for(int i=0;i<16;i++)
		m_origen_copy[i]=vMatriz[i];
	
	for(k=0;k<columnas-1;k++)
	{
		for(i = k + 1; i < columnas; i++)
		{
			if(m_origen_copy[k*4+k] == 0)
			{
				for(int pi=0;pi<4;pi++)
				{
					for(int pj=0;pj<4;pj++)
						if(pi!=pj)
							vRetorno[pi*4+pj]=0.0;
						else
							vRetorno[pi*4+pj]=1.0;
				}
				return false;
			}
			factor = m_origen_copy[i*4+k]/m_origen_copy[k*4+k];
			m_origen_copy[i*4+k] = factor;
			if(factor)
			{
				for(j = k + 1; j < columnas; j++)
				{
					m_origen_copy[i*4+j] -= factor*m_origen_copy[k*4+j];
				}
			}
		}
	}
	for(j=0;j<columnas;j++)
	{
		for (i = 0; i < columnas; i++) 
		{
			b[i] = (i==j)?1.0f:0.0f;
		}

		for(i = 1;i<columnas;i++)
		{                    
			sum=b[i];
			for(k=0;k<i;k++)
				sum=sum-m_origen_copy[i*4+k]*b[k];
			b[i]=sum;
		}

		vRetorno[(columnas-1)*4+j]=b[columnas-1]/m_origen_copy[(columnas-1)*4+(columnas-1)];
		
		for(i=columnas;i>0;i--)
		{
			sum=0;
			for(k = i; k < columnas; k++)
				sum=sum + m_origen_copy[(i-1)*4+k]*vRetorno[k*4+j];
			vRetorno[(i-1)*4+j]=(b[i-1]-sum)/m_origen_copy[(i-1)*4+(i-1)];
		}
	}
	delete b;

	return true;
};


void Zero(stVertex &vValue)
{
	vValue.x = vValue.y = vValue.z = 0.0f;
};

void Infinite(stVertex &vValue)
{
	vValue.x = vValue.y = vValue.z = BIGGESTVALUE;
};

void SetEqual(stVertex &vValue,float vChange)
{
	vValue.x = vValue.y = vValue.z = vChange;
};
void SetFull(stVertex &vValue,float vChangeX,float vChangeY,float vChangeZ)
{
	vValue.x = vChangeX;
	vValue.y = vChangeY;
	vValue.z = vChangeZ;
};

void Limpiar(stVertex &vValue)
{
	if(IsSmall(vValue.x)) vValue.x = 0.0f;
	if(IsSmall(vValue.y)) vValue.y = 0.0f;
	if(IsSmall(vValue.z)) vValue.z = 0.0f;
};

void Igualar(stVertex &vValue,stVertex v2)
{
	vValue.x = v2.x;vValue.y = v2.y;vValue.z = v2.z;
};

void Amplificar(stVertex &vValue ,float vAlfa )
{
	vValue.x = vAlfa * vValue.x;
	vValue.y = vAlfa * vValue.y;
	vValue.z = vAlfa * vValue.z;
};

void Amplificar(stVertex &vValue,stVertex v2 ,float vAlfa)
{
	vValue.x = vAlfa * v2.x;
	vValue.y = vAlfa * v2.y;
	vValue.z = vAlfa * v2.z;
};

void Amplificar(stVertex &vValue,float vAlfa,stVertex v2 )
{
	Amplificar(vValue,v2,vAlfa );
};

void Suma(stVertex &vValue ,stVertex v1, stVertex v2)
{
   vValue.x=v1.x + v2.x;
   vValue.y=v1.y + v2.y;
   vValue.z=v1.z + v2.z;
}; 

void Resta(stVertex &vValue ,stVertex v1, stVertex v2)
{
   vValue.x=v1.x - v2.x;
   vValue.y=v1.y - v2.y;
   vValue.z=v1.z - v2.z;
}; 

void MultiplicacionPuntual(stVertex &vValue ,stVertex v1, stVertex v2)
{
	vValue.x = v1.x * v2.x;
	vValue.y = v1.y * v2.y;
	vValue.z = v1.z * v2.z;
}; 


// COn retorno
stVertex Suma(stVertex v1, stVertex v2)
{
	stVertex temp;
	Suma(temp,v1,v2);
	return temp;
}; 

stVertex Resta(stVertex v1, stVertex v2)
{
	stVertex temp;
	Resta(temp,v1,v2);
	return temp;
}; 

// Othes

float Distancia(stVertex v1 ,stVertex v2)
{
	stVertex temp;
	temp.x = v1.x - v2.x;
	temp.y = v1.y - v2.y;
	temp.z = v1.z - v2.z; 
	return LengthVector(temp);
};

float NormalizeR(stVertex &vValue)
{
    float lengthsq = sqrt(vValue.x*vValue.x + vValue.y*vValue.y + vValue.z*vValue.z);

	if (IsSmall(lengthsq))
    {
        return 0.0f;
    }
    else
    {
        vValue.x /= lengthsq;
        vValue.y /= lengthsq;
        vValue.z /= lengthsq;
    }
	return lengthsq;
};

void Cross(stVertex &vValue ,stVertex v1, stVertex v2)
{
   vValue.x=v1.y*v2.z - v1.z*v2.y;
   vValue.y=v1.z*v2.x - v1.x*v2.z;
   vValue.z=v1.x*v2.y - v1.y*v2.x;
}; 

float CrossNormalize(stVertex &vValue ,stVertex v1, stVertex v2)
{
	Cross(vValue,v1,v2);
	Limpiar(vValue);
	return NormalizeR(vValue);
}; 

float Dot(stVertex v1 ,stVertex v2)
{
	return v1.x*v2.x + v1.y*v2.y +v1.z*v2.z; 
};

float DireccionByResta(stVertex &vPRayo ,stVertex vFin,stVertex vInicio)
{
	Resta(vPRayo,vFin,vInicio);
	Limpiar(vPRayo);
	return NormalizeR(vPRayo);
};

bool Perpendicular(stVertex &vPerpendicular, stVertex vVector) // perpendicular a un vector normalizado
{
	register unsigned i,indiceAdd,indiceAddAdd;
	register float *vector,*perpendicular;

	vector = new float[3];
	perpendicular = new float[3];

	Igualar(vector,vVector);
	for(i = 0; i < 3; i++)
	{
		if(fabs(vector[i]) >= (1.0f/sqrt(3.0f)))
		{
			indiceAdd = (i == 2)? 0: (i + 1);
			indiceAddAdd = (i != 0)? (i - 1): 2;
			perpendicular[indiceAdd] = 1.0f;
			perpendicular[indiceAddAdd] = 0.0f;
			perpendicular[i] = -vector[indiceAdd] / vector[i];

			Igualar(vPerpendicular,perpendicular);
			NormalizeR(vPerpendicular);
			return true;
		}
	}
	return false;
};

void Ray(stVertex &vPRayo ,stVertex vInicio,stVertex vDireccion, float vAlfa)
{
	Amplificar(vPRayo,vAlfa,vDireccion);
	Suma(vPRayo,vInicio,vPRayo);
};

void Ray(stVertex &vPRayo ,stVertex vInicio, float vAlfa, stVertex vDireccion)
{
	Amplificar(vPRayo,vAlfa,vDireccion);
	Suma(vPRayo,vInicio,vPRayo);
};

float 	DistanciaAPlano(stVertex vNormalT , stVertex vDirMov, stVertex vPuntoPlano,stVertex vPuntoInteres)
{
	// Ecuacion Plano Triangulo N*X+d=0
	//d1 = - Dot(normalT,vTriangulo[0]);
	if(!IsSmall(Dot(vNormalT,vDirMov)))
	{
		return  -(- Dot(vNormalT,vPuntoPlano) + Dot(vNormalT,vPuntoInteres)) / Dot(vNormalT,vDirMov);
	}
	return BIGGESTVALUE;
};

float 	DistanciaAPlanoN(stVertex vNormalT , stVertex vPuntoPlano,stVertex vPuntoInteres)
{
	// Ecuacion Plano Triangulo N*X+d=0
	//d1 = - Dot(normalT,vTriangulo[0]);
	return  -(- Dot(vNormalT,vPuntoPlano) + Dot(vNormalT,vPuntoInteres));
};


bool IsPointInTriangle(stVertex vNormal,stVertex vPunto,stVertex vTriangulo[3])
{
	float A[3];
	short i0,i1;
	/* first project onto an axis-aligned plane, that maximizes the area */
	/* of the triangles, compute indices: i0,i1. */
	A[0]=fabs(vNormal.x);
	A[1]=fabs(vNormal.y);
	A[2]=fabs(vNormal.z);
	if(A[0]>A[1])
	{
		if(A[0]>A[2])  
		{
			i0=1;      /* A[0] is greatest */
			i1=2;
		}
		else
		{
			i0=0;      /* A[2] is greatest */
			i1=1;
		}
	}
	else   /* A[0]<=A[1] */
	{
		if(A[2]>A[1])
		{
			i0=0;      /* A[2] is greatest */
			i1=1;                                           
		}
		else
		{
			i0=0;      /* A[1] is greatest */
			i1=2;
		}
	}               
	
	float point[] = {vPunto.x,vPunto.y,vPunto.z};
	float t1[] = {vTriangulo[0].x,vTriangulo[0].y,vTriangulo[0].z};
	float t2[] = {vTriangulo[1].x,vTriangulo[1].y,vTriangulo[1].z};
	float t3[] = {vTriangulo[2].x,vTriangulo[2].y,vTriangulo[2].z};
	POINT_IN_TRI(point,t1,t2,t3);
	return false;
};

bool IsPointInTriangleS(stVertex vNormal,stVertex vPunto,stVertex vTriangulo[3]) // Calculo algebraico
{
	float a,b,c,pA,pB,pC;
	float semiPT,semiPPAB,semiPPAC,semiPPBC;
	float surfaceT,surfacePAB,surfacePAC,surfacePBC;
	stVertex temp;

	Resta(temp,vTriangulo[2],vTriangulo[1]);
	a = LengthVector(temp);
	Resta(temp,vTriangulo[0],vTriangulo[2]);
	b = LengthVector(temp);
	Resta(temp,vTriangulo[1],vTriangulo[0]);
	c = LengthVector(temp);

	Resta(temp,vTriangulo[0],vPunto);
	pA = LengthVector(temp);
	Resta(temp,vTriangulo[1],vPunto);
	pB = LengthVector(temp);
	Resta(temp,vTriangulo[2],vPunto);
	pC = LengthVector(temp);

	semiPT		= (a + b + c)/2.0f;
	semiPPAB	= (pA + pB + c)/2.0f;
	semiPPAC	= (pA + b + pC)/2.0f;
	semiPPBC	= (a + pB + pC)/2.0f;

	surfaceT	= sqrtf(semiPT*(semiPT-a)*(semiPT-b)*(semiPT-c));
	surfacePAB	= sqrtf(semiPPAB*(semiPPAB-pA)*(semiPPAB-pB)*(semiPPAB-c));
	surfacePAC	= sqrtf(semiPPAC*(semiPPAC-pA)*(semiPPAC-b)*(semiPPAC-pC));
	surfacePBC	= sqrtf(semiPPBC*(semiPPBC-a)*(semiPPBC-pB)*(semiPPBC-pC));
	
	if(IsSmall(surfaceT - surfacePAB - surfacePAC - surfacePBC))
		return true;

	return false;
};

bool IsPointInTriangleN(stVertex vNormal,stVertex vPunto,stVertex vTriangulo[3]) // Calculo algebraico
{
	stVertex dir10,dir21,dir02,temp;

	DireccionByResta(temp,vTriangulo[1],vTriangulo[0]);
	CrossNormalize(dir10,temp,vNormal);
	DireccionByResta(temp,vTriangulo[2],vTriangulo[1]);
	CrossNormalize(dir21,temp,vNormal);
	DireccionByResta(temp,vTriangulo[0],vTriangulo[2]);
	CrossNormalize(dir02,temp,vNormal);

	Zero(temp);
	Suma(temp,temp,vTriangulo[0]);
	Suma(temp,temp,vTriangulo[1]);
	Suma(temp,temp,vTriangulo[2]);
	Amplificar(temp,(1.0f/3.0f));

	if(DistanciaAPlanoN(dir10,vTriangulo[0],temp) < 0.0f) // Hcaer que las tres normales apunten al exterior del triangulo
	{
		Amplificar(dir10,-1.0f);
		Amplificar(dir21,-1.0f);
		Amplificar(dir02,-1.0f);
	}

	if( (DistanciaAPlanoN(dir10,vTriangulo[0],vPunto) >= 0.0f)
		&& (DistanciaAPlanoN(dir21,vTriangulo[1],vPunto) >= 0.0f)
		&& (DistanciaAPlanoN(dir02,vTriangulo[2],vPunto) >= 0.0f))
	{
		return true;
	}
	return false;
};

bool IsPointInTriangleA(stVertex vNormal,stVertex vPunto,stVertex vTriangulo[3],int vTipoAnalisis) // Calculo algebraico
{
	register unsigned i;
	register float alfa,ampliacion = 10.0f;
	stVertex dir,temp;

	Zero(temp);
	for(i = 0; i < 3; i++)
	{
		Suma(temp,temp,vTriangulo[i]);
	}
	Amplificar(temp,(1.0f/3.0f)); // Baricentro

	// Expandir universo
	for(i = 0; i < 3; i++)
	{
		alfa = DireccionByResta(dir,vTriangulo[i],temp);
		Ray(vTriangulo[i],temp,alfa * ampliacion,dir);
	}
	alfa = DireccionByResta(dir,vPunto,temp);
	Ray(vPunto,temp,alfa * ampliacion,dir);

	switch(vTipoAnalisis)
	{
		case 0:
			return IsPointInTriangle(vNormal,vPunto,vTriangulo); // Daniel Test
			break;
		case 1:
			return IsPointInTriangleS(vNormal,vPunto,vTriangulo); // Surface Test
			break;
		case 2:
			return IsPointInTriangleN(vNormal,vPunto,vTriangulo); // Normal Segments Test
			break;
		default:
			return IsPointInTriangle(vNormal,vPunto,vTriangulo);
			break;
	}
};

bool IsPointInTriangleB(stVertex vNormal,stVertex vPunto,stVertex vTriangulo[3]) // Calculo Bizarro
{
	if( IsSmall(Distancia(vTriangulo[0],vPunto)) || IsSmall(Distancia(vTriangulo[1],vPunto)) || IsSmall(Distancia(vTriangulo[2],vPunto)))
	{
		return true;	
	}

	register unsigned i;
	register float radioMax;
	stVertex temp;

	Zero(temp);
	for(i = 0; i < 3; i++)
	{
		Suma(temp,temp,vTriangulo[i]);
	}
	Amplificar(temp,(1.0f/3.0f)); // Baricentro

	// Radio maximo
	radioMax = 0.0f;
	for(i = 0; i < 3; i++)
	{
		if(Distancia(temp,vTriangulo[i]) > radioMax)
		{
			radioMax = Distancia(temp,vTriangulo[i]);
		}
	}

	if(Distancia(vPunto,temp) > radioMax)
	{
		return false;
	}
	else
	{
		return true;
	}
}

void OrdenarValoresMinMax(float* vValue,unsigned vDimension)
{
	register unsigned i,j,k;
	register float temp;

	for(i=0; i< vDimension; i++)
	{
		for(j=0; j< i; j++)
		{
			if(vValue[i] < vValue[j])// muere
			{
				temp = vValue[i];
				for(k = i; k > j ; k--)
				{
					vValue[k] = vValue[k-1];
				}
				vValue[j] = temp;
			}
		}
	}
};

int InterseccionRayoEsfera(float *vAlfas, stVertex vOrigen, stVertex vDireccion, stVertex vCentro, float vRadio) // Indica si hay colision entre un rayo y una esfera... retorna el numero de contactos 
{
	return 0;
};

bool InterseccionClosedRayoEsfera(float *vAlfa, stVertex vOrigen, stVertex vDireccion, stVertex vCentro, float vRadio) // Indica si hay colision valida (alfa > 0.0f) y entrega el valor de alfa mas cercano al origen del rayo
{
	register bool valido = false;
	register unsigned i;
	float *alfas = new float[2];
	InterseccionRayoEsfera(alfas,vOrigen,vDireccion,vCentro,vRadio);

	vAlfa[0] = BIGGESTVALUE;
	for(i = 0; i < 2; i++)
	{
		if(alfas[i] > 0.0f && alfas[i] < vAlfa[0])
		{
			valido = true;
			vAlfa[0] = alfas[i];
		}
	}

	return valido;
};

bool InterseccionFarestRayoEsfera(float *vAlfa, stVertex vOrigen, stVertex vDireccion, stVertex vCentro, float vRadio) // Indica si hay colision valida (alfa > 0.0f) y entrega el valor de alfa mas lejano al origen del rayo
{
	register bool valido = false;
	register unsigned i;
	float *alfas = new float[2];
	InterseccionRayoEsfera(alfas,vOrigen,vDireccion,vCentro,vRadio);

	vAlfa[0] = 0.0f;
	for(i = 0; i < 2; i++)
	{
		if(alfas[i] > vAlfa[0])
		{
			valido = true;
			vAlfa[0] = alfas[i];
		}
	}

	return valido;
};
