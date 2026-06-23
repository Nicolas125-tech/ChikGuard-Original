# Diário do Artemis 🦅

## 2026-06-23 - Estabilização Numérica do Ângulo Tibiotársico (Hock Angle)
**Anomalia:** Ocorrência de `RuntimeWarning: invalid value encountered in arccos` e geração de valores `nan` durante a estimativa do Hock Angle em sequências rápidas ou com oclusões parciais das articulações da ave.
**Aprendizado Matemático:** O ruído de detecção nas coordenadas normalizadas da pélvis ($P_1$), jarrete ($P_2$) e pata ($P_3$) gera vetores cujo produto escalar dividido pelo produto das normas resulta ligeiramente fora do intervalo $[-1.0, 1.0]$ (ex: $1.00000004$) devido a imprecisões de ponto flutuante de precisão simples. Adicionalmente, quando dois keypoints são detectados na mesma coordenada, a magnitude de um dos vetores se torna zero, levando a um erro de divisão por zero.
**Prevenção:** Implementar salvaguarda que valida se as normas de $\vec{u}$ ou $\vec{v}$ são nulas (retornando $0.0$) e aplicar explicitamente `np.clip` no cosseno calculado limitando-o no intervalo $[-1.0, 1.0]$ antes de submetê-lo ao `np.arccos`.
