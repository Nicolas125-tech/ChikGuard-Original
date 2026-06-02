/* global process */
import { createClient } from '@supabase/supabase-js';

// Carregar variáveis do .env ou passar diretamente (neste teste, vamos assumir que o .env.local foi preenchido)
import dotenv from 'dotenv';
dotenv.config({ path: '.env.local' });

const supabaseUrl = process.env.VITE_SUPABASE_URL || 'http://localhost:54321'; // fallback local
const supabaseKey = process.env.VITE_SUPABASE_ANON_KEY || 'dummy_key';

const supabase = createClient(supabaseUrl, supabaseKey);

async function testSupabase() {
  console.log('--- Iniciando Teste de Conexão com o Supabase ---');

  // Verifica se as chaves existem
  if (!process.env.VITE_SUPABASE_URL || !process.env.VITE_SUPABASE_ANON_KEY) {
      console.warn('⚠️ AVISO: VITE_SUPABASE_URL ou VITE_SUPABASE_ANON_KEY não estão definidas no arquivo .env.local.');
      console.warn('Por favor, preencha essas variáveis com as credenciais do seu projeto Supabase e tente novamente.');
      // Vamos tentar executar assim mesmo para demonstrar a resposta de erro
  }

  const ufo_name = 'Disco Voador Teste';
  const ufo_local = 'Varginha, MG - Brasil';
  const ufo_date = new Date().toISOString().split('T')[0];

  try {
    console.log(`1. Inserindo UFO de teste (${ufo_name} em ${ufo_local})...`);

    // Inserção
    const { data: insertData, error: insertError } = await supabase
      .from('ufos')
      .insert([
        { nome: ufo_name, local_aparicao: ufo_local, data_avistamento: ufo_date }
      ])
      .select(); // pede para retornar o dado inserido

    if (insertError) {
      throw insertError;
    }

    console.log('✅ Inserção bem-sucedida!');
    console.log('Dados inseridos:', insertData);

    console.log('\n2. Buscando UFOs na tabela...');

    // Busca
    const { data: selectData, error: selectError } = await supabase
      .from('ufos')
      .select('*')
      .limit(5);

    if (selectError) {
      throw selectError;
    }

    console.log('✅ Busca bem-sucedida!');
    console.log('UFOs encontrados:', selectData);

    console.log('\n--- Teste Concluído com Sucesso ---');

  } catch (error) {
    console.error('\n❌ ERRO NA COMUNICAÇÃO COM O SUPABASE ❌');
    console.error('Detalhes do erro:');
    console.error(error.message || error);

    if (error.code === 'PGRST116' || error.message?.includes('does not exist')) {
        console.error('\n> DICA: Parece que a tabela "ufos" não existe. Você executou o script supabase/migrations/create_ufos.sql no SQL Editor do Supabase?');
    }
  }
}

testSupabase();
