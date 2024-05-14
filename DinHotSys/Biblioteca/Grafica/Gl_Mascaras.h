#pragma once
#include "OGL.h"

class GL_Mascaras : public OGL
{
private:

public:
	GL_Mascaras(void);
	~GL_Mascaras(void);
	virtual void Resize(int w, int h);
			void Resize(unsigned vDimVentanaX, unsigned vDimVentanaY, unsigned vResMaskX, unsigned vResMaskY);
	virtual void Renderizar(float **vMatriz,unsigned vX, unsigned vY);
};
