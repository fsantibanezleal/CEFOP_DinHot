#pragma once
#include "OGL.h"
#include "BasicFunctions.h"

#define factorDim	(1000000.0f)

class GL_Trampas : public OGL
{
private:

public:
	GL_Trampas(void);
	~GL_Trampas(void);
	virtual void Resize(int vDimVentanaX, int vDimVentanaY);
	virtual void Renderizar(stVertex *vPosicionTrampas,unsigned vNumTrampas);
};
